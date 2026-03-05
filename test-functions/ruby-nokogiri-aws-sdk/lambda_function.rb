require 'json'
require 'net/http'
require 'uri'
require 'nokogiri'
require 'aws-sdk-core'

def lambda_handler(event:, context:)
  # Test nokogiri: fetch and parse HTML
  url = event['url'] || 'https://jsomers.net'
  uri = URI.parse(url)
  response = Net::HTTP.get_response(uri)
  raise "HTTP #{response.code} fetching #{url}" unless response.is_a?(Net::HTTPSuccess)

  doc = Nokogiri::HTML(response.body)
  title = doc.at('title')&.text || 'no title'
  heading = doc.at('h1')&.text || 'no h1'

  # Test aws-sdk-core: verify STS caller identity
  sts = Aws::STS::Client.new
  identity = sts.get_caller_identity
  account_id = identity.account

  {
    statusCode: 200,
    body: JSON.generate({
      nokogiri_version: Nokogiri::VERSION,
      aws_sdk_core_version: Aws::CORE_GEM_VERSION,
      parsed_title: title,
      parsed_heading: heading,
      aws_account_id: account_id
    })
  }
end
