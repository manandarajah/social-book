import React from 'react';
import 'bootstrap/dist/css/bootstrap.css';
import Navbar from './components/Navbar';
import LeftSidebar from './components/LeftSidebar';
import Feed from './components/Feed';
import RightSidebar from './components/RightSidebar';
import Profile from './components/Profile/Profile';

// Note: For Bootstrap styling, ensure Bootstrap CSS is included in your index.html or imported in your project.

function App() {

  const [current_user, setCurrentUser] = React.useState({});
  const csrf_token = getCsrfTokenFromCookie();

  React.useEffect(() => {

    //if (csrf_token) {
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
    //}
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
      {current_user.is_verified && (
        <div style={{ minHeight: '100vh' }}>
          {!path.endsWith("/") && <Profile current_user={current_user} get_cookie={getCsrfTokenFromCookie} />}
          {path.endsWith("/") && <Navbar current_user={current_user} get_cookie={getCsrfTokenFromCookie} />}
          {path.endsWith("/") && (
            <div className="container-fluid mt-4">
              <div className="row">
                <LeftSidebar current_user={current_user}/>
                <Feed current_user={current_user} get_cookie={getCsrfTokenFromCookie} />
                <RightSidebar />
              </div>
            </div>
          )}
        </div>)}
        {!current_user.is_verified && (
          <form action="/logout" method="POST">
            <span>Your account is not verified. Check your email and verify your account before you can use this app!</span><br/>
            <button type="submit" className="btn btn-link p-0">Click here to sign into a different account</button>
            <input type="hidden" name="csrf_token" value={csrf_token} />
          </form>
        )}
    </div>
  );
}

export default App;
