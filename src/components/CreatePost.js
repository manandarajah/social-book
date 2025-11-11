import React from 'react';

function CreatePost(props) {
    const current_user = props.current_user;
    const placeholder = "What's on your mind, "+current_user.first_name+"?";
    const csrf_token = props.get_cookie();

    return (
        <div className="card mb-3 shadow-sm">
            <div className="card-body">
                <form method='POST' action='/create-post' enctype="multipart/form-data">
                    <div className="d-flex align-items-center mb-2">
                        <img
                            src={current_user.profile_picture}
                            alt="User"
                            className="rounded-circle me-2"
                            name="profile_picture"
                            width="40"
                            height="40"
                        />
                        <input
                            type="text"
                            className="form-control rounded-pill"
                            name="content"
                            placeholder={placeholder}
                        />
                    </div>
                    <div className="d-flex justify-content-between mt-2">
                        <button className="btn btn-light d-flex align-items-center">
                            <i className="bi bi-camera-video-fill text-danger me-1"></i> Live Video
                        </button>
                        {/* <button className="btn btn-light d-flex align-items-center">
                            <i className="bi bi-image-fill text-success me-1"></i> Photo/Video
                        </button> */}
                        <input type="file" className="btn btn-light d-flex align-items-center" name="attachment" />
                        <button className="btn btn-light d-flex align-items-center">
                            <i className="bi bi-emoji-smile-fill text-warning me-1"></i> Feeling/Activity
                        </button>
                        <input type="submit" class="btn btn-primary brand-button d-flex align-items-center" value="Create Post" />
                    </div>
                    <input type="hidden" name="csrf_token" value={csrf_token} />
                </form>
            </div>
        </div>
    );
}

export default CreatePost;
