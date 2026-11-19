const { jestConfig } = require('@salesforce/sfdx-lwc-jest/config');

module.exports = {
    ...jestConfig,
    moduleNameMapper: {
        ...jestConfig.moduleNameMapper,
        // The template compiler lowercases the namespace of <FlowToolKit-flow-form>, so the stub is mapped under that name.
        '^flowtoolkit/flowForm$': '<rootDir>/jest/stubs/FlowToolKit/flowForm/flowForm'
    }
};
