import _ from 'lodash';
import axios from 'axios';

export const handler = async (event) => {
  const url = event.url || 'https://jsomers.net';
  const response = await axios.get(url);
  const title = response.data.match(/<title>(.*?)<\/title>/)?.[1] || 'no title';

  return {
    statusCode: 200,
    body: JSON.stringify({
      lodash_version: _.VERSION,
      axios_version: axios.VERSION,
      parsed_title: title,
    }),
  };
};
