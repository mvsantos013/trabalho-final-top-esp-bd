import axios from 'axios'

const BASE_PATH = 'http://localhost:5005'

const validateUrl = (url) => {
  return axios.post(`${BASE_PATH}/validate`, { url })
}

export default {
  validateUrl,
}
