import { axe } from "jest-axe";

export function runAccessibilityCheck(container: Element) {
  return axe(container, {
    rules: {
      region: { enabled: false },
    },
  });
}
