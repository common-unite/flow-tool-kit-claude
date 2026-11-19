import { LightningElement } from 'lwc';
// Flow Tool Kit loads section components by name, which an LWR site's publisher cannot see; these imports make it bundle them.
import 'c/feeSummarySection';

export default class CustomSectionsLwrSupport extends LightningElement {}
