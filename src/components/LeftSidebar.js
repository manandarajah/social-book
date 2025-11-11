import React from 'react';

function LeftSidebar(props) {
    const current_user = props.current_user;
    const path = '/'+current_user.username;

    return (
        <div className="col-2 d-none d-md-block">
            <div className="card border-0 bg-transparent">
                <ul className="list-group list-group-flush">
                    <li className="list-group-item bg-transparent border-0 d-flex align-items-center">
                        <img
                            src={current_user.profile_picture}
                            alt="User"
                            className="rounded-circle me-2"
                            width="36"
                            height="36"
                        />
                        <span className="fw-semibold"><a href={path} class='text-white'>{current_user.first_name} {current_user.last_name}</a></span>
                    </li>
                    <li className="list-group-item bg-transparent border-0 d-flex align-items-center">
                        <i className="bi bi-people-fill me-2" style={{ color: '#1877f2', fontSize: '1.3rem' }}></i>
                        <span>Friends</span>
                    </li>
                    <li className="list-group-item bg-transparent border-0 d-flex align-items-center">
                        <i className="bi bi-clock-history me-2" style={{ color: '#1877f2', fontSize: '1.3rem' }}></i>
                        <span>Memories</span>
                    </li>
                    <li className="list-group-item bg-transparent border-0 d-flex align-items-center">
                        <i className="bi bi-bookmark-fill me-2" style={{ color: '#1877f2', fontSize: '1.3rem' }}></i>
                        <span>Saved</span>
                    </li>
                    <li className="list-group-item bg-transparent border-0 d-flex align-items-center">
                        <i className="bi bi-flag-fill me-2" style={{ color: '#1877f2', fontSize: '1.3rem' }}></i>
                        <span>Pages</span>
                    </li>
                </ul>
            </div>
        </div>
    );
}

export default LeftSidebar;
