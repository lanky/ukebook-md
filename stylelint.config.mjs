/** @type {import('stylelint').Config} */
export default {
  extends: [
    "stylelint-config-standard",
    "stylelint-config-recommended",
    "stylelint-config-alphabetical-order",
  ],
  rules: {
    "block-no-empty": true,
  },
};
