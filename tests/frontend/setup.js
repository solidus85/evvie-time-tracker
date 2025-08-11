/**
 * Jest setup file for frontend tests
 */

// Add custom matchers from jest-dom
import '@testing-library/jest-dom';

// Mock fetch API
import fetchMock from 'jest-fetch-mock';
fetchMock.enableMocks();

// Reset mocks before each test
beforeEach(() => {
    fetch.resetMocks();
    localStorage.clear();
    sessionStorage.clear();
    document.body.innerHTML = '';
});

// Global test utilities
global.createMockResponse = (data, status = 200) => {
    return Promise.resolve({
        ok: status >= 200 && status < 300,
        status,
        json: () => Promise.resolve(data),
        text: () => Promise.resolve(JSON.stringify(data))
    });
};

// Mock DOM elements commonly used
global.createMockElement = (tagName, attributes = {}) => {
    const element = document.createElement(tagName);
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'innerHTML') {
            element.innerHTML = value;
        } else {
            element.setAttribute(key, value);
        }
    });
    return element;
};

// Mock date/time for consistent testing
const mockDate = new Date('2024-01-08T10:00:00.000Z');
global.Date = class extends Date {
    constructor(...args) {
        if (args.length === 0) {
            super(mockDate);
        } else {
            super(...args);
        }
    }
    
    static now() {
        return mockDate.getTime();
    }
};