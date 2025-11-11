import React from 'react';
import Dropdown from 'react-bootstrap/Dropdown';
import Comments from './Comments/Comments';

function ViewPost(props) {
    const post = props.post;
    const time_diff = Date.now() - new Date(post.created_at).getTime();
    const current_user = props.current_user;
    const csrf_token = props.get_cookie();
    const second = 1000; //1 second in milliseconds
    const minute = 60000; //1 minute in milliseconds
    const hour = 3600000; //1 hour in milliseconds
    const day = 86400000; // 1 day in milliseconds

    return (
        <div className="card mb-3 shadow-sm" key={post}>
            <div className="card-body">
                {current_user.current_user && current_user.username === post.username && (
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
                        <a href={post.profile_url} className="brand-link fw-semibold">
                            {post.first_name} {post.last_name}
                        </a>
                        <div className="text-muted" style={{ fontSize: '0.9rem' }}>
                            {time_diff > day && (
                                <span>{new Date(post.created_at).toDateString()}</span>
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
                    <button className="btn btn-light flex-fill">
                        <i className="bi bi-share me-1"></i> Share
                    </button>
                </div>
                <Comments post={post} current_user={current_user} get_cookie={props.get_cookie} />
            </div>
            <form className="d-flex justify-content-between bg-secondary-subtle p-2" method="post" action='/comment-post'>
                <img
                    src={current_user.profile_picture}
                    alt="User"
                    className="rounded-circle me-2"
                    width="40"
                    height="40"
                />
                <input
                    type="text"
                    className="form-control rounded-pill"
                    name="content"
                    placeholder="Post comment here"
                />
                <input type="submit" className="btn btn-primary brand-button d-flex align-items-center rounded-circle mx-2" value="P" />
                <input type="hidden" name="id" value={post._id} />
                <input type="hidden" name="csrf_token" value={csrf_token} />
            </form>
        </div>
    )
}

export default ViewPost;