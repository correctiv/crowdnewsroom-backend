import React, {Component} from 'react';
import { DropdownV2, InlineNotification } from "carbon-components-react";
import {authorizedFetch, authorizedPUT} from "./api";

export default class BucketPicker extends Component {
  constructor(props){
    super(props);
    this.state = {
      currentState: null,
      updated: false,
    };

    this.updateSelection = this.updateSelection.bind(this);
    this.update = this.update.bind(this);
    this.clearSoon = this.clearSoon.bind(this);
  }

  componentDidMount(){
    console.log(this.props);
    const responsePromise = authorizedFetch(`/forms/responses/${this.props.responseId}`);
    responsePromise.then(formResponse => {
      this.setState({currentState: formResponse.status})
    })
  }

  clearSoon(){
    setTimeout(() => {
      this.setState({updated:false})
    }, 3000);
  }

  update(updatedResponse){
      this.setState({currentState: updatedResponse.status, updated: true}, this.clearSoon)
  }

  updateSelection({selectedItem}){
    authorizedPUT(`/forms/responses/${this.props.responseId}`,
      {body: JSON.stringify({status: selectedItem.id})}
    ).then(this.update);
  }

  render(){
    if (!this.state.currentState){
      return <div>Loading</div>
    }

    const items = [{id: "S", text: gettext("Inbox")},
                   {id: "V", text: gettext("Verified")},
                   {id: "I", text: gettext("Trash")}];

    const currentItem = items.find(item => item.id === this.state.currentState);

    return <div>
      <DropdownV2
        itemToString={item => item.text}
        label="Bucket"
        items={items}
        initialSelectedItem={currentItem}
        onChange={this.updateSelection}
        />
      {this.state.updated && <InlineNotification
        title="Status updated"
        subtitle=""
        iconDescription="close this notification"
        kind="success"
      /> }
    </div>
  }
}

