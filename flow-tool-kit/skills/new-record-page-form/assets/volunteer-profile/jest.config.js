const { jestConfig } = require('@salesforce/sfdx-lwc-jest/config');

module.exports = {
    ...jestConfig,
    moduleNameMapper: {
        ...jestConfig.moduleNameMapper,
        // The template compiler lowercases the namespace of <flowtoolkit-lightning-record-form>, so the stub is mapped under that name.
        '^flowtoolkit/lightningRecordForm$': '<rootDir>/jest/stubs/flowtoolkit/lightningRecordForm/lightningRecordForm'
    }
};
