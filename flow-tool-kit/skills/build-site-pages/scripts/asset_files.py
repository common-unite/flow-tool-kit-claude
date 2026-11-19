#!/usr/bin/env python3
"""Turn the photos a page needs into web-ready public Asset Files that a guest can load.

    asset_files.py --manifest photos.json --assets-dir force-app/main/default/contentassets convert <source folder>
    asset_files.py --manifest photos.json --assets-dir <same> finish --target-org <org-alias>   after deploying the converted files
    asset_files.py --manifest photos.json --assets-dir <same> upload --target-org <org-alias>   the same files through the data API, then finish

The manifest is JSON: {"folder": "<Asset Library folder>", "photos": [{"name": "<api name>", "label": "...",
"description": "...", "source": "<file inside the source folder>", "width": <pixels>}]}. Nothing is guessed: both paths
are required arguments.

convert writes, per photo, a progressive JPEG at the given width under 700 KB and its .asset-meta.xml (public, in the
Asset Library), ready to deploy. It needs Pillow and nothing else, so it runs in claude.ai chat too.
finish sets each file's title and description (Asset File metadata carries neither) and moves it into the folder.
upload is for an org you do not deploy source to: a file inserted with IsAssetEnabled becomes an Asset File, the same as
one uploaded by hand in the Asset Library. finish and upload change the org and need the Salesforce CLI.
"""
import argparse
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import time

LIBRARY = 'sfdc_asset_company_assets'
API = '/services/data/v62.0'
TARGET_BYTES = 700_000
QUALITIES = (85, 82, 78, 74, 70, 66)
META = '''<?xml version="1.0" encoding="UTF-8"?>
<ContentAsset xmlns="http://soap.sforce.com/2006/04/metadata">
    <isVisibleByExternalUsers>true</isVisibleByExternalUsers>
    <language>en_US</language>
    <masterLabel>{label}</masterLabel>
    <relationships>
        <organization>
            <access>VIEWER</access>
        </organization>
        <workspace>
            <access>INFERRED</access>
            <isManagingWorkspace>true</isManagingWorkspace>
            <name>sfdc_asset_company_assets</name>
        </workspace>
    </relationships>
    <versions>
        <version>
            <number>1</number>
            <pathOnClient>{name}.jpg</pathOnClient>
        </version>
    </versions>
</ContentAsset>
'''


def xml_text(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def encode(source, width, quality):
    from PIL import Image, ImageOps
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        if image.width > width:
            image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
        out = io.BytesIO()
        image.save(out, 'JPEG', quality=quality, optimize=True, progressive=True)
        return out.getvalue()


def convert(assets, photos, source_folder):
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit('asset_files.py: convert needs Pillow (pip install Pillow)')
    os.makedirs(assets, exist_ok=True)
    for photo in photos:
        source = os.path.join(source_folder, photo['source'])
        for quality in QUALITIES:
            image = encode(source, int(photo['width']), quality)
            if len(image) <= TARGET_BYTES: break
        if len(image) > TARGET_BYTES:
            sys.exit(f'asset_files.py: {photo["name"]} is {len(image)} bytes at quality {quality}; give it a smaller width')
        with open(os.path.join(assets, f'{photo["name"]}.asset'), 'wb') as file: file.write(image)
        with open(os.path.join(assets, f'{photo["name"]}.asset-meta.xml'), 'w', encoding='utf-8') as file:
            file.write(META.format(name=photo['name'], label=xml_text(photo['label'])))
        print(f'{photo["name"]:36} {os.path.getsize(source) / 1048576:5.1f} MB -> {len(image) / 1024:4.0f} KB  width {photo["width"]}  quality {quality}')


def sf(*command):
    done = subprocess.run(['sf', *command, '--json'], capture_output=True, text=True)
    text = done.stdout[done.stdout.find('{'):] if '{' in done.stdout else '{}'
    data = json.loads(text)
    if done.returncode != 0 or data.get('status', 0) != 0:
        sys.exit(f'asset_files.py: sf {command[0]} {command[1]} failed: {data.get("message", done.stderr)[:400]}')
    return data.get('result')


def query(org, soql):
    return sf('data', 'query', '--target-org', org, '--query', soql)['records']


def rest(org, method, path, body):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as file: json.dump(body, file)
    try:
        for attempt in range(5):
            done = subprocess.run(['sf', 'api', 'request', 'rest', API + path, '--method', method, '--body', '@' + file.name, '--target-org', org], capture_output=True, text=True)
            # back-to-back writes to one library can find its row still locked by the write before
            if 'UNABLE_TO_LOCK_ROW' not in done.stdout: break
            time.sleep(5)
    finally:
        os.unlink(file.name)
    if done.returncode != 0: sys.exit(f'asset_files.py: {method} {path} failed: {(done.stdout + done.stderr)[:400]}')
    return json.loads(done.stdout) if done.stdout.strip() else None


def save(org, method, records):
    results = rest(org, method, '/composite/sobjects', {'allOrNone': True, 'records': records})
    if not all(result['success'] for result in results): sys.exit(f'asset_files.py: {results}')
    return [result['id'] for result in results]


def in_list(values):
    return ', '.join("'" + str(value).replace("'", "\\'") + "'" for value in values)


def finish(org, manifest, photos):
    library = query(org, f"SELECT Id, RootContentFolderId FROM ContentWorkspace WHERE DeveloperName = '{LIBRARY}'")[0]
    assets = query(org, f'SELECT DeveloperName, ContentDocumentId FROM ContentAsset WHERE DeveloperName IN ({in_list(photo["name"] for photo in photos)})')
    documents = {asset['DeveloperName']: asset['ContentDocumentId'] for asset in assets}
    missing = [photo['name'] for photo in photos if photo['name'] not in documents]
    if missing: sys.exit(f'asset_files.py: not in the org yet: {missing}. Deploy the converted files, or run upload.')
    save(org, 'PATCH', [{'attributes': {'type': 'ContentDocument'}, 'Id': documents[photo['name']], 'Title': photo['label'], 'Description': photo.get('description', '')} for photo in photos])
    if not library.get('RootContentFolderId'):
        # an Asset Library that has never held a folder has no root folder to file under
        print(f'{len(photos)} titles and descriptions set. The Asset Library has no folders yet: create "{manifest["folder"]}" there once (Files, Libraries, Asset Library, New Folder), then run finish again to file the photos in it.')
        return
    folder_name = manifest['folder'].replace("'", "\\'")
    folders = query(org, f"SELECT Id FROM ContentFolder WHERE Name = '{folder_name}' AND ParentContentFolderId = '{library['RootContentFolderId']}'")
    folder_id = folders[0]['Id'] if folders else save(org, 'POST', [{'attributes': {'type': 'ContentFolder'}, 'Name': manifest['folder'], 'ParentContentFolderId': library['RootContentFolderId']}])[0]
    members = query(org, f"SELECT Id FROM ContentFolderMember WHERE ChildRecordId IN ({in_list(documents.values())}) AND ParentContentFolderId = '{library['RootContentFolderId']}'")
    if members: save(org, 'PATCH', [{'attributes': {'type': 'ContentFolderMember'}, 'Id': member['Id'], 'ParentContentFolderId': folder_id} for member in members])
    print(f'{len(photos)} titles and descriptions set, {len(members)} files moved into "{manifest["folder"]}"')


def upload(org, assets, manifest, photos):
    library = query(org, f"SELECT Id FROM ContentWorkspace WHERE DeveloperName = '{LIBRARY}'")[0]
    organization_id = query(org, 'SELECT Id FROM Organization')[0]['Id']
    existing = {asset['DeveloperName'] for asset in query(org, f'SELECT DeveloperName FROM ContentAsset WHERE DeveloperName IN ({in_list(photo["name"] for photo in photos)})')}
    for photo in photos:
        if photo['name'] in existing: continue
        with open(os.path.join(assets, f'{photo["name"]}.asset'), 'rb') as file: image = base64.b64encode(file.read()).decode()
        version = rest(org, 'POST', '/sobjects/ContentVersion', {'Title': photo['label'], 'PathOnClient': f'{photo["name"]}.jpg', 'Description': photo.get('description', ''),
                                                                 'VersionData': image, 'IsAssetEnabled': True, 'FirstPublishLocationId': library['Id']})
        document_id = query(org, f"SELECT ContentDocumentId FROM ContentVersion WHERE Id = '{version['id']}'")[0]['ContentDocumentId']
        asset = query(org, f"SELECT Id, DeveloperName FROM ContentAsset WHERE ContentDocumentId = '{document_id}'")[0]
        save(org, 'PATCH', [{'attributes': {'type': 'ContentAsset'}, 'Id': asset['Id'], 'DeveloperName': photo['name'], 'MasterLabel': photo['label'], 'IsVisibleByExternalUsers': True}])
        # a deployed or hand-uploaded public Asset File is also shared with the whole org as viewer
        save(org, 'POST', [{'attributes': {'type': 'ContentDocumentLink'}, 'ContentDocumentId': document_id, 'LinkedEntityId': organization_id, 'ShareType': 'V', 'Visibility': 'AllUsers'}])
        print(f'{photo["name"]} created')
    finish(org, manifest, photos)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--manifest', required=True, help='photos.json')
    parser.add_argument('--assets-dir', required=True, help="the project's contentassets folder (written by convert, read by upload)")
    parser.add_argument('command', choices=['convert', 'finish', 'upload'])
    parser.add_argument('source', nargs='?', help='convert: the folder holding the source photos')
    parser.add_argument('--target-org', help='finish and upload: the org alias')
    args = parser.parse_args(argv)
    with open(args.manifest, encoding='utf-8') as file: manifest = json.load(file)
    photos = manifest['photos']
    assets = os.path.abspath(args.assets_dir)
    if args.command == 'convert':
        if not args.source: parser.error('convert needs the source photo folder')
        convert(assets, photos, args.source)
    else:
        if not args.target_org: parser.error(f'{args.command} needs --target-org')
        if args.command == 'finish': finish(args.target_org, manifest, photos)
        else: upload(args.target_org, assets, manifest, photos)


if __name__ == '__main__':
    main()
