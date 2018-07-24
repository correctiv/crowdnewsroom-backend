import React, {Component} from "react";
import ReactDOM from "react-dom";
import {
  DataTable,
  DropdownV2,
  TextInput,
  Form,
  FormGroup,
  Button,
  DataTableSkeleton
} from "carbon-components-react";
import {authorizedDELETE, authorizedFetch, authorizedPOST} from "./api";
import {assign, snakeCase, find, endsWith, keyBy} from "lodash";


const {
  TableContainer,
  Table,
  TableHead,
  TableHeader,
  TableRow,
  TableBody,
  TableCell,
  TableToolbar,
  TableBatchActions,
  TableBatchAction,
  TableSelectRow,
  TableSelectAll,
  TableToolbarSearch,
} = DataTable;


const getAvailableRoles = (user) => {
  const roles = [
    {id: "A", text: "Admin"},
    {id: "E", text: "Editor"},
    {id: "V", text: "Viewer"},
  ];
  const ownerRole = {id: "O", text: "Owner"};
  if (user.role === "O"){
    roles.unshift(ownerRole)
  }
  return roles;
}

function RoleDropdown({selectedRole, user, updateCallback, availableRoles}) {
  const initialRole = availableRoles.find(role => role.id === selectedRole);

  // we might not have found an initial role because the user that is logged
  // in is and admin but they are seeing an owner whose role the cannot change
  if (user.is_requester || !initialRole){
    const roleKey = selectedRole.substr(0,1);
    const names = {
      "A": "Admin",
      "O": "Owner"
    };
    return <div>{names[roleKey]}</div>
  }

  if (initialRole) {
    return <DropdownV2
      label={"role"}
      onChange={(event) => updateCallback(user.id, event.selectedItem.id)}
      itemToString={item => item.text}
      initialSelectedItem={initialRole}
      items={availableRoles}
    />
  }
  return <div>Wat?</div>
}

function ManageRoleCell({row, changeUserCallback, availableRoles}){
  const isInvitation = !row.role;
  if (isInvitation){
    return <TableCell><i>Invitation Pending</i></TableCell>;
  }
  return <TableCell>
    <RoleDropdown selectedRole={row.role}
                user={row}
                updateCallback={changeUserCallback}
                availableRoles={availableRoles} />
  </TableCell>
}

const renderTableWithUpdate = (updateCallback, removeUsers, availableRoles, originalRows) => {
  const keyedRows = keyBy(originalRows, "email");

  return ({ rows, headers, getHeaderProps, getBatchActionProps, getSelectionProps, selectedRows, onInputChange, getRowProps }) => (
    <TableContainer>
      <TableToolbar>
        <TableBatchActions {...getBatchActionProps()}>
          <TableBatchAction onClick={() => removeUsers(selectedRows)}
                            icon="close"
                            iconDescription="remove">
            Remove
          </TableBatchAction>
        </TableBatchActions>
        <TableToolbarSearch onChange={onInputChange}/>
      </TableToolbar>
      <Table>
        <TableHead>
          <TableRow>
            <TableSelectAll {...getSelectionProps()} />
            {headers.map(header => (
              <TableHeader {...getHeaderProps({ header }) }>
                {header.header}
              </TableHeader>
            ))}
            <TableHeader>
              Rolle
            </TableHeader>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(row => <TableRow key={row.id} {...getRowProps({row, id:row.id})}>
              <TableSelectRow {...getSelectionProps({ row })} />
              {row.cells.map(cell => <TableCell key={cell.id}>{cell.value}</TableCell>)}
              <ManageRoleCell row={keyedRows[row.id]} availableRoles={availableRoles} changeUserCallback={updateCallback}/>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>);
}

class InviteUser extends Component {
  constructor(props){
    super(props);
    this.state = {email: ""};

    this.updateEmail = this.updateEmail.bind(this);
    this.submit = this.submit.bind(this);
  }

  updateEmail(event){
    this.setState({email: event.target.value});
  }

  submit(event){
    event.preventDefault();
    this.props.inviteCallback(this.state.email)
  }

  render() {
    return <Form onSubmit={this.submit}>
      <FormGroup>
        <div className="invite-users">
          <TextInput
            invalidText={this.props.error}
            invalid={this.props.error !== null}
            labelText="Email"
            value={this.state.email}
            onChange={this.updateEmail}
          />
          <div className="bx--form-item invite-users--button" >
            <Button onClick={this.submit}>Einladen</Button>
          </div>
        </div>
        <div>
          Enter the email of the collaborator you would like to invite. This persons will receive an email and will be able to create an account.
        </div>
      </FormGroup>
    </Form>
  }
}

function removeUser(user, investigationSlug) {
  return authorizedDELETE(`/forms/investigations/${investigationSlug}/groups/${user.role}/users/${user.id}`)
}

function removeInvitation(invitation) {
  return authorizedDELETE(`/forms/invitations/${invitation.id}`)
}

class App extends Component {
    constructor(props){
        super(props);
        const [match, slug] = window.location.pathname.match(/investigations\/([a-z-]+)\/users/);
        this.state = {
            users: [],
            invitations: [],
            emailError: null,
            currentUser: null,
            slug
        };
        this.updateUserRole = this.updateUserRole.bind(this);
        this.loadUsers = this.loadUsers.bind(this);
        this.loadInvitations = this.loadInvitations.bind(this);
        this.inviteUser = this.inviteUser.bind(this);
        this.removeUsers = this.removeUsers.bind(this);
    }

    componentDidMount(){
      this.loadUsers();
      this.loadInvitations();
    }

    inviteUser(email){
      const handleError = (error) => {
        error.response.json().then(json => {
          if (json.email){
            this.setState({emailError: json.email[0]})
          }
          else {
            const tr = document.getElementById(email);
            tr.classList.add("shake");
            setTimeout(() => tr.classList.remove("shake"), 800)
          }
        });
      };

      authorizedPOST(`/forms/investigations/${this.state.slug}/invitations`, {body: JSON.stringify({email})})
        .then(this.setState({emailError: null}))
        .then(this.loadInvitations)
        .catch(handleError);
    }

    loadUsers(){
      authorizedFetch(`/forms/investigations/${this.state.slug}/users`).then(json => {
        const currentUser = json.users.find(user => user.is_requester);
        this.setState({users: json.users, currentUser});
      })
    }

    loadInvitations(){
      authorizedFetch(`/forms/investigations/${this.state.slug}/invitations`).then(invitations => {
        this.setState({invitations: invitations.filter(invitation => invitation.accepted === null)});
      })
    }

    updateUserRole(userID, role){
      const payload = {id: userID};
      authorizedPOST(`/forms/investigations/${this.state.slug}/groups/${role}/users`, {body: JSON.stringify(payload)})
        .then(this.loadUsers)
    }

    removeUsers(users){
      const userEmails = users.map(user => user.id);
      const selectedUsers = this.state.users.filter(user => userEmails.indexOf(user.email) !== -1);
      const selectedInvitations = this.state.invitations.filter(user => userEmails.indexOf(user.email) !== -1)

      const removeUserPromises = selectedUsers.map(user => removeUser(user, this.state.slug));
      Promise.all(removeUserPromises).then(this.loadUsers);

      const removeInvitationPromises = selectedInvitations.map(invitation => removeInvitation(invitation));
      Promise.all(removeInvitationPromises).then(this.loadInvitations);
    }


    render() {
      const combinedUsers = this.state.users.concat(this.state.invitations);

      if (!combinedUsers.length || !this.state.currentUser){
        return <DataTableSkeleton/>
      }

      const rows = combinedUsers.map(user => {
        return assign({}, user, {id: user.email})
      });

      const availableRoles = getAvailableRoles(this.state.currentUser);

      const headers = [{key: "first_name", header: "Vorname"},
                       {key: "last_name", header: "Nachname"},
                       {key: "email", header: "E-Mail"}];
        return <div className="investigation-users">
          <div className="investigation-users--section">
            Invite members of your team to help contribute to your investigation by assigning them specific permissions. Each collaborator will be able to access your project through their own Crowdnewsroom account. As the creator, you remain ultimately responsible for your project and for your team's interactions with contributors. Pick collaborators that you trust and that will do a good job working with your community. Have questions about how this works? Visit our FAQ.
          </div>

          <div className="investigation-users--section">
            <h2>Invite a new Collaborator</h2>
            <InviteUser inviteCallback={this.inviteUser} error={this.state.emailError}/>
          </div>

          <div className="cnr--datatable-overflowable investigation-users--section">
            <h2>Manage the collaborators</h2>
            <DataTable
                rows={rows}
                headers={headers}
                render={renderTableWithUpdate(this.updateUserRole, this.removeUsers, availableRoles, combinedUsers)}/>
            <div>
              <dl className="roles-list">
                <dt className="roles-list--dt">Admin</dt>
                <dd className="roles-list--dd">An admin can manage the investigation settings page & the collaborators </dd>

                <dt className="roles-list--dt">Editor</dt>
                <dd className="roles-list--dd">The editor can see everything about the data collected via this investigation</dd>

                <dt className="roles-list--dt">Viewer</dt>
                <dd className="roles-list--dd">A viewer can see the data collected via this investigation but is not able to modify; to sort it or to download it</dd>

              </dl>
            </div>
          </div>
        </div>;
    }
}

const rootElement = document.getElementById("user-management");
ReactDOM.render(<App />, rootElement);
