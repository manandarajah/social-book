import React from 'react';
import Dropdown from 'react-bootstrap/Dropdown';

function ViewPost(props) {
    const post = props.post;
    const currentUser = props.current_user;
    const csrf_token = props.get_cookie();
    const second = 1000; //1 second in milliseconds
    const minute = 60000; //1 minute in milliseconds
    const hour = 3600000; //1 hour in milliseconds
    const day = 86400000; // 1 day in milliseconds

    return (
        <div className="card mb-3 shadow-sm" key={post}>
            <div className="card-body">
                {currentUser.current_user && currentUser.username === post.username && (
                    <Dropdown className="float-end">
                        <Dropdown.Toggle variant="success" className="btn btn-light" id="dropdown-basic">
                            ...
                        </Dropdown.Toggle>

                        <Dropdown.Menu>
                            <Dropdown.Item>
                                <i className="bi bi-pencil-square text-primary" onClick={() => props.edit(post.id, true)}>Edit</i>
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
                        <a href={post.url} className="fw-semibold">
                            {post.first_name} {post.last_name}
                        </a>
                        <div className="text-muted" style={{ fontSize: '0.9rem' }}>
                            {new Date(post.current_time) - new Date(post.created_at) > day && (
                                <span>{new Date(post.created_at).toDateString()}</span>
                            )}
                            {(new Date(post.current_time) - new Date(post.created_at) > hour
                                && new Date(post.current_time) - new Date(post.created_at) < day) && (
                                <span>{Math.floor((new Date(post.current_time) - new Date(post.created_at))/hour)} hours</span>
                            )}
                            {(new Date(post.current_time) - new Date(post.created_at) > minute
                                && new Date(post.current_time) - new Date(post.created_at) < hour) && (
                                <span>{Math.floor((new Date(post.current_time) - new Date(post.created_at))/minute)} minutes</span>
                            )}
                            {(new Date(post.current_time) - new Date(post.created_at) > second
                                && new Date(post.current_time) - new Date(post.created_at) < minute) && (
                                <span>{Math.floor((new Date(post.current_time) - new Date(post.created_at))/second)} seconds</span>
                            )}
                            {new Date(post.current_time) - new Date(post.created_at) <= second && (
                                <span>Just now</span>
                            )}
                            <i className="bi bi-globe-americas"></i>
                        </div>
                    </div>
                </div>
                <div className="mb-2">
                    {post.content}
                </div>
                {post.attachment && (
                    <img
                    src={post.attachment}
                    alt="Post"
                    className="img-fluid rounded mb-2"
                />)}
                <div className="d-flex justify-content-between">
                    <button className="btn btn-light flex-fill me-1">
                        <i className="bi bi-hand-thumbs-up me-1"></i> Like
                    </button>
                    <button className="btn btn-light flex-fill me-1">
                        <i className="bi bi-chat-left-text me-1"></i> Comment
                    </button>
                    <button className="btn btn-light flex-fill">
                        <i className="bi bi-share me-1"></i> Share
                    </button>
                </div>
            </div>
        </div>
    )
}

export default ViewPost;