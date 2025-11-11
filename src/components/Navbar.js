import React from 'react';

function Navbar(props) {
    const current_user = props.current_user;
    const [showDropdown, setShowDropdown] = React.useState(false);
    const csrf_token = props.get_cookie();

    // Function to handle clicking outside the dropdown to close it
    React.useEffect(() => {
        function handleClickOutside(event) {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target) &&
                profileImgRef.current &&
                !profileImgRef.current.contains(event.target)
            ) {
                setShowDropdown(false);
            }
        }
        if (showDropdown) {
            document.addEventListener("mousedown", handleClickOutside);
        } else {
            document.removeEventListener("mousedown", handleClickOutside);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [showDropdown]);

    const dropdownRef = React.useRef(null);
    const profileImgRef = React.useRef(null);

    return (
        <nav className="navbar navbar-expand-lg navbar-light bg-white shadow-sm px-3">
            <a className="navbar-brand fw-bold" href="/" style={{ fontSize: '1.7rem', color: '#003333' }}>
                SocialSite
            </a>
            <form className="d-none d-md-flex ms-3" role="search">
                <input
                    className="form-control me-2"
                    type="search"
                    placeholder="Search SocialBook"
                    aria-label="Search"
                    style={{ width: 250 }}
                />
            </form>
            <div className="ms-auto d-flex align-items-center position-relative">
                <img
                    ref={profileImgRef}
                    src={current_user.profile_picture}
                    alt="Profile"
                    className="rounded-circle"
                    width="36"
                    height="36"
                    style={{ cursor: "pointer" }}
                    onClick={() => setShowDropdown((prev) => !prev)}
                />
                {showDropdown && (
                    <div
                        ref={dropdownRef}
                        className="dropdown-menu dropdown-menu-end show mt-2"
                        style={{
                            position: "absolute",
                            top: "100%",
                            right: 0,
                            minWidth: "150px",
                            boxShadow: "0 0.5rem 1rem rgba(0,0,0,.15)",
                            zIndex: 1000,
                        }}
                    >
                        <form action="/logout" method="POST">
                            <button type="submit" className="dropdown-item">
                                Logout
                            </button>
                            <input type="hidden" name="csrf_token" value={csrf_token} />
                        </form>
                    </div>
                )}
            </div>
        </nav>
    );
}

export default Navbar;
