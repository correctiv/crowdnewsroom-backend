import React, {Component} from 'react';
import { DropdownV2, InlineNotification } from "carbon-components-react";
import {authorizedFetch, authorizedPUT} from "./api";

const INBOX_LABEL = gettext('Inbox');
const VERIFIED_LABEL = gettext('Verified');
const TRASH_LABEL = gettext('Trash');

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

    const items = [{id: "S", text: INBOX_LABEL},
                   {id: "V", text: VERIFIED_LABEL},
                   {id: "I", text: TRASH_LABEL}];


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
        title={gettext("Status updated")}
        subtitle=""
        iconDescription={gettext("close this notification")}
        kind="success"
      /> }
    </div>
  }
}

