require 'json'
require 'net/http'
require 'uri'
require 'nokogiri'
require 'aws-sdk-s3'

S3 = Aws::S3::Client.new
BUCKET = ENV['BUCKET_NAME']

def lambda_handler(event:, context:)
  url = event['url'] || 'https://example.com'
  uri = URI.parse(url)

  # Fetch HTML
  response = Net::HTTP.get_response(uri)
  raise "HTTP #{response.code} fetching #{url}" unless response.is_a?(Net::HTTPSuccess)

  html = response.body
  doc = Nokogiri::HTML(html)

  # Generate outputs
  markdown = to_markdown(doc.at('body') || doc)
  plaintext = doc.text.gsub(/[ \t]+/, ' ').gsub(/\n{3,}/, "\n\n").strip

  # Write to S3
  hostname = uri.host
  timestamp = Time.now.strftime('%Y%m%d-%H%M%S')
  md_key = "#{hostname}/#{timestamp}.md"
  txt_key = "#{hostname}/#{timestamp}.txt"

  S3.put_object(bucket: BUCKET, key: md_key, body: markdown, content_type: 'text/markdown')
  S3.put_object(bucket: BUCKET, key: txt_key, body: plaintext, content_type: 'text/plain')

  {
    statusCode: 200,
    body: {
      url: url,
      md_key: md_key,
      txt_key: txt_key,
      md_length: markdown.length,
      txt_length: plaintext.length
    }
  }
end

# --- Recursive DOM → Markdown converter ---

def to_markdown(node)
  return '' if node.nil?
  out = walk(node)
  out.gsub(/\n{3,}/, "\n\n").strip + "\n"
end

def walk(node)
  return handle_text(node) if node.text?
  return '' if node.comment?

  case node.name
  when 'h1'       then "\n# #{children_text(node).strip}\n\n"
  when 'h2'       then "\n## #{children_text(node).strip}\n\n"
  when 'h3'       then "\n### #{children_text(node).strip}\n\n"
  when 'h4'       then "\n#### #{children_text(node).strip}\n\n"
  when 'h5'       then "\n##### #{children_text(node).strip}\n\n"
  when 'h6'       then "\n###### #{children_text(node).strip}\n\n"
  when 'p'        then "\n#{children_text(node).strip}\n\n"
  when 'br'       then "  \n"
  when 'strong', 'b' then "**#{children_text(node).strip}**"
  when 'em', 'i'  then "*#{children_text(node).strip}*"
  when 'a'
    href = node['href']
    text = children_text(node).strip
    href ? "[#{text}](#{href})" : text
  when 'img'
    alt = node['alt'] || ''
    src = node['src'] || ''
    "![#{alt}](#{src})"
  when 'blockquote'
    inner = children_text(node).strip
    inner.lines.map { |l| "> #{l}" }.join
  when 'ul'
    items = node.css('> li').map { |li| "- #{children_text(li).strip}" }
    "\n#{items.join("\n")}\n\n"
  when 'ol'
    items = node.css('> li').each_with_index.map { |li, i| "#{i + 1}. #{children_text(li).strip}" }
    "\n#{items.join("\n")}\n\n"
  when 'li'
    children_text(node)
  when 'script', 'style', 'noscript'
    ''
  else
    children_text(node)
  end
end

def children_text(node)
  node.children.map { |c| walk(c) }.join
end

def handle_text(node)
  text = node.text
  # Collapse whitespace in inline context but preserve meaningful content
  text.gsub(/[ \t]+/, ' ')
end
