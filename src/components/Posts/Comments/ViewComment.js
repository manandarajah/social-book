import React from 'react';
import Dropdown from 'react-bootstrap/Dropdown';

function ViewComment(props) {
    const comment = props.comment;
    const time_diff = Date.now() - new Date(comment.created_at).getTime();
    const current_user = props.current_user;
    const csrf_token = props.get_cookie();
    const second = 1000; // 1 second in ms
    const minute = 60000;
    const hour = 3600000;
    const day = 86400000;

    return (
        <div className="pt-2">
            <div className="d-flex align-items-start mb-3">
                <img
                    src={comment.profile_picture}
                    alt="User"
                    className="rounded-circle me-2"
                    width="32"
                    height="32"
                />
                <div className="bg-light rounded p-2 flex-grow-1">
                    {current_user.current_user && current_user.username === comment.username && (
                        <Dropdown className="float-end">
                            <Dropdown.Toggle variant="success" className="btn btn-light" id="dropdown-basic">
                                ...
                            </Dropdown.Toggle>

                            <Dropdown.Menu>
                                <Dropdown.Item>
                                    <i className="bi bi-pencil-square text-primary" onClick={() => props.edit(comment.id, true)}>Edit</i>
                                </Dropdown.Item>
                                <Dropdown.Item>
                                    <i className="bi bi-trash text-danger" onClick={() => props.delete(props.post_id, comment.id, csrf_token)}>Delete</i>
                                </Dropdown.Item>
                            </Dropdown.Menu>
                        </Dropdown>
                    )}
                    <a href={comment.profile_url} className="brand-link fw-semibold">
                        {comment.first_name} {comment.last_name}
                    </a>
                    <div>
                        {time_diff > day && (
                            <span>{new Date(comment.created_at).toDateString()}</span>
                        )}
                        {(time_diff > hour && time_diff < day) && (
                            <span>{Math.floor((time_diff) / hour)} hours</span>
                        )}
                        {(time_diff > minute && time_diff < hour) && (
                            <span>{Math.floor((time_diff) / minute)} minutes</span>
                        )}
                        {(time_diff > second && time_diff < minute) && (
                            <span>{Math.floor((time_diff) / second)} seconds</span>
                        )}
                        {time_diff <= second && (
                            <span>Just now</span>
                        )}
                    </div>
                    <div>{comment.content}</div>
                </div>
            </div>
        </div>
    );
}

export default ViewComment;
