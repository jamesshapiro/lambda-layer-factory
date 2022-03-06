/////////////////PROD//////////////////
// npm run build
// PROD: aws s3 cp --recursive build/ s3://cdkhabits-githabitcombucket6a79c338-hk3nkues0h5f
// PROD: aws cloudfront create-invalidation --distribution-id E2WZ67Q81CV1B5 --paths "/*"
// FFB: npm run build && aws s3 cp --recursive build/ s3://cdkhabits-githabitcombucket6a79c338-hk3nkues0h5f && aws cloudfront create-invalidation --distribution-id E2WZ67Q81CV1B5 --paths "/*"
/////////////////PROD//////////////////
// npm run build
// DEV: aws s3 cp --recursive build/ s3://cdkhabits-habitsweakerpotionscombucketdff06391-116yh481gtpp6
// DEV: aws cloudfront create-invalidation --distribution-id E70XD704NPJDM --paths "/*"
import './App.css'
import React from 'react'

class App extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      layerName: '',
      language: 'python',
      runtimes: [],
      dependencies: [''],
    }
  }

  handleLayerNameChange(event) {
    //let username = this.state.username
    console.log(event.target.value)
    this.setState({ language: event.target.value })
  }

  handleLanguageChange(event) {
    //let username = this.state.username
    console.log(event.target.value)
    this.setState({ layerName: event.target.value })
  }

  handleRuntimeChange(event) {
    //let username = this.state.username
    let options = event.target.options
    let value = []
    for (let i = 0, l = options.length; i < l; i++) {
      if (options[i].selected) {
        value.push(options[i].value)
      }
    }
    console.log(value)
    this.setState({ runtimes: value })
  }

  handleSelect(event) {
    console.log(event.target.value)
    // this.setState({ username: event.target.value })
  }

  addClick() {
    this.setState((prevState) => ({
      dependencies: [...prevState.dependencies, ''],
    }))
  }

  removeClick(i) {
    let dependencies = [...this.state.dependencies]
    dependencies.splice(i, 1)
    this.setState({ dependencies })
  }

  handleSubmit = (i) => {
    console.log('handling submit')
    const url = process.env.REACT_APP_REQUEST_LAYER_URL
    const headers = {}
    const final_url = url
    fetch(final_url, {
      method: 'GET',
      headers: headers,
    }).then((response) => {
      console.log(response)
    })
  }

  getRuntimes = () => {
    if (this.state.language === 'python') {
      return (
        <select
          onChange={this.handleRuntimeChange.bind(this)}
          name="runtimes"
          id="runtimes"
          multiple
        >
          <option value="python3.6">Python 3.6</option>
          <option value="python3.7">Python 3.7</option>
          <option value="python3.8">Python 3.8</option>
          <option value="python3.9">Python 3.9</option>
        </select>
      )
    }
  }

  createUI = () => {
    return (
      <>
        <table className="habit-ui-table">
          <tbody>
            <tr>
              <td>User Input:</td>
              <td className="td-textarea">
                <input
                  placeholder={'[layer name here (optional)]'}
                  className="bullet-textarea"
                  onChange={this.handleLayerNameChange.bind(this)}
                />
              </td>
            </tr>
            <tr>
              <td>Language</td>
              <td>
                <select
                  onChange={this.handleLanguageChange.bind(this)}
                  name="language"
                  id="language"
                >
                  <option value="python">Python</option>
                  <option value="node">Node</option>
                </select>
              </td>
            </tr>

            {this.state.dependencies.map((el, i) => (
              <tr key={i}>
                <td className="td-button">
                  <div
                    type="button"
                    className="bullet-button"
                    value="+"
                    onClick={this.addClick.bind(this)}
                  >
                    +
                  </div>
                </td>
                <td className="td-textarea">
                  <textarea
                    value={el || ''}
                    className="bullet-textarea"
                    onChange={this.handleLayerNameChange.bind(this, i)}
                  />
                </td>
                <td className="td-button">
                  <div
                    type="button"
                    className="bullet-button"
                    value="-"
                    onClick={this.removeClick.bind(this, i)}
                  >
                    -
                  </div>
                </td>
              </tr>
            ))}
            <tr>
              <td>{this.getRuntimes()}</td>
            </tr>
            <tr>
              <td></td>
              <td>
                <div
                  type="button"
                  className="create-layer-button"
                  onClick={this.addClick.bind(this)}
                >
                  Create Layer!
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </>
    )
  }

  componentDidMount() {
    // this.getNewEntries()
  }

  getEditHabitsMode = () => {
    return (
      <div>
        <div className="App">
          <div className="nav-bar-div">
            <span className="left-elem">
              <span className="nav-bar-cell habit-tracker-header">
                Lambda Layer Factory
              </span>
            </span>
          </div>
          {this.createUI()}
        </div>
        <div className="blank-footer" />
      </div>
    )
  }

  getMainView = () => {
    return this.getEditHabitsMode()
  }

  render() {
    return this.getMainView()
  }
}

export default App
