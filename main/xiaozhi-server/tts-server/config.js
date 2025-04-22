module.exports = {
  // ttsFrontendPort: 8083,
  ttsFrontendPort: process.env.NODE_ENV=='dev' ? 8183 : 8083,
};
