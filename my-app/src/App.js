// npm run build && aws s3 cp --recursive build/ s3://layerfactory-lambdalayerfactorycombucketef8645bd-dwllqbzsmy6p && aws cloudfront create-invalidation --distribution-id E1LIL67TZCUW2P --paths "/*"
import './App.css';
import React from 'react'

import { useInput } from './hooks/input-hook'

export function NameForm(props) {
  const {
    value: firstName,
    bind: bindFirstName,
    reset: resetFirstName,
  } = useInput('')
  const {
    value: lastName,
    bind: bindLastName,
    reset: resetLastName,
  } = useInput('')

  const handleSubmit = (evt) => {
    evt.preventDefault()
    alert(`Submitting Name ${firstName} ${lastName}`)
    resetFirstName()
    resetLastName()
  }
  return (
    <form onSubmit={handleSubmit}>
      <label>
        First Name:
        <input type="text" {...bindFirstName} />
      </label>
      <label>
        Last Name:
        <input type="text" {...bindLastName} />
      </label>
      <input type="submit" value="Submit" />
    </form>
  )
}

function App() {
  const url = process.env.REACT_APP_LAMBDA_LAYER_FACTORY_URL
  return (
    <div>
      <div>Shalom Haverim! {url}</div>
      <div><NameForm></NameForm></div>
    </div>
  )
}

export default App;
