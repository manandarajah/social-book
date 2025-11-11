import React from 'react';
import Dropdown from 'react-bootstrap/Dropdown';

function EditPost(props) {
    const [post, setPost] = React.useState(props.post);
    const csrf_token = props.get_cookie();
    const current_user = props.current_user;

    // Handle input changes
    const handleChange = (e) => {
        setPost(prev => ({
            ...prev,
            content: e.target.value
        }));
    };

    return (
        <div className="card mb-3 shadow-sm" >
            <div className="card-body">
                {current_user.current_user && current_user.username === post.username && (
                    <Dropdown className="float-end">
                        <Dropdown.Toggle variant="success" className="btn btn-light" id="dropdown-basic">
                            ...
                        </Dropdown.Toggle>

                        <Dropdown.Menu>
                            <Dropdown.Item>
                                <i className="bi bi-x-circle text-secondary" onClick={() => props.edit(post.id, false)}>Cancel</i>
                            </Dropdown.Item>
                            <Dropdown.Item>
                                <i className="bi bi-trash text-danger" onClick={() => props.delete(post.id, csrf_token)}>Delete</i>
                            </Dropdown.Item>
                        </Dropdown.Menu>
                    </Dropdown>
                )}
                <div className="d-flex align-items-center mb-2">
                    <img
                        src={post.profile_picture}
                        alt="User"
                        className="rounded-circle me-2"
                        width="40"
                        height="40"
                    />
                    <div>
                        <div className="fw-semibold">
                            {post.first_name} {post.last_name}
                        </div>
                    </div>
                </div>
                <form className="mb-2" method='POST' action='/update-post'>
                    <input type="text" className="form-control rounded-pill" name="content" onChange={handleChange} value={post.content} />
                    <input type="hidden" name="id" value={post._id} />
                    {post.attachment && (
                        <img
                        src={post.attachment}
                        alt="Post"
                        className="img-fluid rounded mb-2"
                    />)}
                    <input type="submit" class="btn btn-primary brand-button" value="Save" />
                    <input type="hidden" name="csrf_token" value={csrf_token} />
                </form>
            </div>
        </div>
    )
}

export default EditPost;