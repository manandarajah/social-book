import React from 'react';
import Dropdown from 'react-bootstrap/Dropdown';

function EditComment(props) {
    const [comment, setComment] = React.useState(props.comment);
    const csrf_token = props.get_cookie ? props.get_cookie() : '';
    const current_user = props.current_user;

    // Handle input changes
    const handleChange = (e) => {
        setComment(prev => ({
            ...prev,
            content: e.target.value
        }));
    };

    return (
        <div className="pt-5">
            {current_user.current_user && current_user.username === comment.username && (
                <Dropdown className="float-end">
                    <Dropdown.Toggle variant="success" className="btn btn-light" id="dropdown-basic">
                        ...
                    </Dropdown.Toggle>
                    <Dropdown.Menu>
                        <Dropdown.Item>
                            <i
                                className="bi bi-x-circle text-secondary"
                                onClick={() => props.edit(comment.id, false)}
                            >
                                Cancel
                            </i>
                        </Dropdown.Item>
                        <Dropdown.Item>
                            <i
                                className="bi bi-trash text-danger"
                                onClick={() => props.delete(props.post_id, comment.id, csrf_token)}
                            >
                                Delete
                            </i>
                        </Dropdown.Item>
                    </Dropdown.Menu>
                </Dropdown>
            )}
            <div className="d-flex align-items-center mb-2">
                <img
                    src={comment.profile_picture}
                    alt="User"
                    className="rounded-circle me-2"
                    width="32"
                    height="32"
                />
                <div>
                    <div className="fw-semibold">
                        {comment.first_name} {comment.last_name}
                    </div>
                </div>
            </div>
            <form className="mb-2" method="POST" action="/update-comment">
                <input
                    type="text"
                    className="form-control rounded-pill"
                    name="content"
                    onChange={handleChange}
                    value={comment.content}
                />
                <input type="hidden" name="post_id" value={props.post_id} />
                <input type="hidden" name="comment_id" value={comment.id} />
                <input type="hidden" name="csrf_token" value={csrf_token} />
                <button
                    type="submit"
                    className="btn btn-primary brand-button mt-2"
                    disabled={!comment.content || comment.content.trim() === ""}
                >
                    Save
                </button>
            </form>
        </div>
    );
}

export default EditComment;
