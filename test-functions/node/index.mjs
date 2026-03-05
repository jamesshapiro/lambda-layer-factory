export const handler = async (event) => {
  const testModules = event.test_imports || ['lodash'];
  const results = {};
  for (const mod of testModules) {
    try {
      const imported = await import(mod);
      const version = imported.VERSION || imported.default?.VERSION || 'unknown';
      results[mod] = { status: 'ok', version };
    } catch (e) {
      results[mod] = { status: 'error', message: e.message };
    }
  }
  return {
    statusCode: 200,
    body: JSON.stringify(results, null, 2),
  };
};
