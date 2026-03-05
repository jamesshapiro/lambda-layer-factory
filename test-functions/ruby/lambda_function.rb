require 'json'

def lambda_handler(event:, context:)
  test_gems = event['test_imports'] || ['nokogiri']
  results = {}
  test_gems.each do |gem_name|
    begin
      require gem_name
      mod = Object.const_get(gem_name.split('-').map(&:capitalize).join)
      version = mod.const_defined?(:VERSION) ? mod::VERSION : 'unknown'
      results[gem_name] = { status: 'ok', version: version }
    rescue LoadError => e
      results[gem_name] = { status: 'error', message: e.message }
    rescue NameError
      results[gem_name] = { status: 'ok', version: 'loaded' }
    end
  end
  {
    statusCode: 200,
    body: JSON.generate(results)
  }
end
