import React from 'react';
import ViewProfile from './ViewProfile';
import EditProfile from './EditProfile';
import Posts from '../Posts/Posts';
import Navbar from '../Navbar';

function Profile(props) {
    const csrf_token = props.get_cookie();
    const [profile, setProfile] = React.useState(null);
    const [update, setUpdate] = React.useState(false);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
        fetch('/api/profile'+window.location.pathname, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf_token
            },
            credentials: 'include',
            body: JSON.stringify({'key':'value'})
        })
        .then(res => {
            if (!res.ok) throw new Error('Failed to fetch profile');
            return res.json();
        })
        .then(data => {
            setProfile(data);
            setLoading(false);
        })
        .catch(err => {
            setError(err.message);
            setLoading(false);
        });
    }, [csrf_token]);

    if (loading) {
        return (
            <div className="container mt-5">
                <div className="text-center">Loading profile...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container mt-5">
                <div className="alert alert-danger text-center">{error}</div>
            </div>
        );
    }

    if (!profile) {
        return (
            <div className="container mt-5">
                <div className="alert alert-warning text-center">No profile data found.</div>
            </div>
        );
    }

    return (
        <div>
            <Navbar current_user={profile} get_cookie={props.get_cookie} />
            <div className="container mt-5" style={{ maxWidth: 600 }}>
                <div className="card shadow-sm">
                    <div className="card-body">
                        {update ? <EditProfile profile={profile} get_cookie={props.get_cookie} /> 
                            : <ViewProfile profile={profile} />}
                        {profile.current_user && !update && (
                            <div className="d-flex flex-column align-items-center mb-4">
                                <button type="button" className="btn btn-primary" onClick={() => setUpdate(true)}>
                                    Update
                                </button>
                            </div>
                        )}
                        {profile.current_user && update && (
                            <div className="d-flex flex-column align-items-center mb-4">
                                <button type="button" className="btn btn-light" onClick={() => setUpdate(false)}>
                                    Cancel
                                </button>
                            </div>
                        )}
                    </div>
                </div>
                <span>{profile.current_user ? "Your Activity:" : profile.first_name + "'s Activity:"}</span>
                <Posts current_user={profile} get_cookie={props.get_cookie} />
            </div>
        </div>
    );
}

export default Profile;


