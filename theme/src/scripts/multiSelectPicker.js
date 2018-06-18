import React, {Component} from 'react';
import { render } from 'react-dom';
import { MultiSelect } from "carbon-components-react";
import {authorizedFetch, authorizedPUT} from "./api";

export default class MultiSelectPicker extends Component {
  constructor(props){
    super(props);
    this.state = {
      items: [],
      selectedItems: []
    };

    this.updateSelection = this.updateSelection.bind(this);
    this.update = this.update.bind(this);
  }

  componentDidMount(){
    const itemPromise =
      authorizedFetch(`/forms/investigations/${this.props.investigationSlug}/${this.props.property}`);

    const responsePromise = authorizedFetch(`/forms/responses/${this.props.responseId}`);

    Promise.all([itemPromise, responsePromise]).then(([items, response]) => {
      const selectedItems = items.filter(item => response[this.props.property].includes(item.id));
      this.setState({items, selectedItems})
    });
  }

  update(updatedResponse){
      const selectedItems = this.state.items.filter(item => updatedResponse[this.props.property].includes(item.id));
      this.setState({selectedItems});
  }

  updateSelection({selectedItems}){
    authorizedPUT(`/forms/responses/${this.props.responseId}`,
      {body: JSON.stringify({[this.props.property]: selectedItems.map(item => item.id)})})
    .then(this.update);
  }

  render(){
    if (!this.state.items.length){
      return <div>Loading</div>
    }

    return <div>
      <MultiSelect
        label={this.props.label}
        itemToString={this.props.itemToString}
        initialSelectedItems={this.state.selectedItems}
        onChange={this.updateSelection}
        items={this.state.items} />
      <ul>
        {this.state.selectedItems.map(item => <li key={item.id}><div className="bx--tag bx--tag--beta">{this.props.itemToString(item)}</div></li>)}
      </ul>
    </div>
  }
}

