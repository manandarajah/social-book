import React from 'react';
import ViewPost from './ViewPost';
import EditPost from './EditPost';

function Posts(props) {
    const csrf_token = props.get_cookie();
    const [posts, setPosts] = React.useState([]);
    // const [loading, setLoading] = React.useState(true);
    // const [error, setError] = React.useState(null);
    var path = window.location.pathname.endsWith("/") ? '' : window.location.pathname;
    var post_counter = 0;

    React.useEffect(() => {
        fetch('/api/posts'+path, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrf_token
            },
            credentials: 'include',
            body: JSON.stringify({'key':'value'})
        })
        .then(res => {
            if (!res.ok) throw new Error('Failed to fetch posts');
            return res.json();
        })
        .then(data => {

            data.posts.map(post => {
                post.id = post_counter++;
                post.profile_url = '/'+post.username;
                post.edit_mode = false;
                post.content = atob(post.content);

                if (post.comments && Array.isArray(post.comments)) {
                    var comment_counter = 0;

                    post.comments = post.comments.map(comment => {
                        // Decode base64-encoded comment content if needed
                        comment.id = comment_counter++;
                        comment.profile_url = '/'+comment.username;
                        comment.edit_mode = false;
                        comment.content = atob(comment.content);

                        return comment;
                    });
                }
            });

            setPosts(data.posts);
            // setLoading(false);
        })
        .catch(err => {
            // setError(err.message);
            // setLoading(false);
            console.log(`Delete failed: ${err.message}`);
        });
    }, []);

    // Function to handle toggling a post's edit_mode
    function handleEditModeChange(postId, value) {
        setPosts(prevPosts =>
            prevPosts.map(post =>
                post.id === postId
                    ? { ...post, edit_mode: value }
                    : post
            )
        );
    }

    // Function to handle deleting a post by ID using form data
    function handleDeletePost(postId, csrf_token) {
        // Find the post to delete
        const post = posts.find(p => p.id === postId);
        if (!post) return;

        const formData = new FormData();
        formData.append('id', post._id);
        formData.append('attachment_id', post.attachment_id);
        formData.append('csrf_token', csrf_token);

        fetch('/delete-post', {
            method: 'POST',
            credentials: 'include',
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error('Failed to delete post');
            // If successful, remove post from state
            setPosts(prevPosts => prevPosts.filter(p => p.id !== postId));
        })
        .catch(err => {
            setError(`Delete failed: ${err.message}`);
        });
    }

    return (
        <div>
            {posts.map((post) => (
                post.edit_mode ? <EditPost post={post} current_user={props.current_user} edit={handleEditModeChange} delete={handleDeletePost} get_cookie={props.get_cookie} /> 
                    : <ViewPost post={post} current_user={props.current_user} edit={handleEditModeChange} delete={handleDeletePost} get_cookie={props.get_cookie} />
            ))}
        </div>
    )
}

export default Posts;
