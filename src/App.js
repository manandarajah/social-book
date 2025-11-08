import React from 'react';
import 'bootstrap/dist/css/bootstrap.css';
import Navbar from './components/Navbar';
import LeftSidebar from './components/LeftSidebar';
import Feed from './components/Feed';
import RightSidebar from './components/RightSidebar';
import Profile from './components/Profile/Profile';

// Note: For Bootstrap styling, ensure Bootstrap CSS is included in your index.html or imported in your project.

function App() {

  const [currentUser, setCurrentUser] = React.useState({});
  const csrf_token = getCsrfTokenFromCookie();

  React.useEffect(() => {

    // if (csrf_token) {
      fetch('/api/current-user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf_token
        },
        credentials: 'include',
        body: JSON.stringify({'key':'value'})
      })
      .then(res => res.json())
      .then(data => setCurrentUser(data))
      .catch(err => setCurrentUser(null));
    // }
  }, [csrf_token]);

  function getCsrfTokenFromCookie() {
    // Read the csrf_token cookie (the readable one)
    const cookies = document.cookie.split(';');
    const csrfCookie = cookies.find(c => c.trim().startsWith('csrf_token='));
    
    if (csrfCookie) {
      return csrfCookie.split('=')[1];
    }

    return null;
  };
  
  const path = window.location.pathname;

  return (
    <div>
      {currentUser.is_verified && (
        <div className="bg-light" style={{ minHeight: '100vh' }}>
          {!path.endsWith("/") && <Profile get_cookie={getCsrfTokenFromCookie} />}
          {path.endsWith("/") && <Navbar current_user={currentUser} get_cookie={getCsrfTokenFromCookie} />}
          {path.endsWith("/") && (
            <div className="container-fluid mt-4">
              <div className="row">
                <LeftSidebar current_user={currentUser}/>
                <Feed current_user={currentUser} get_cookie={getCsrfTokenFromCookie} />
                <RightSidebar />
              </div>
            </div>
          )}
        </div>)}
      {!currentUser.is_verified && (
        <div>
          <span>Your account is not verified. Check your email and verify your account before you can use this app!</span><br/>
          <a href='/logout'>Click here to sign into a different account</a>
        </div>
      )}
    </div>
  );
}

export default App;
