import React from 'react';
import ViewComment from './ViewComment';
import EditComment from './EditComment';

function Comments(props) {
    const post = props.post;
    const [comments, setComments] = React.useState(post.comments);
    // const [error, setError] = React.useState("");

    // Handle edit mode toggle for a comment by id
    const handleEdit = (commentId, value) => {
        setComments(prevComments => 
            prevComments.map(comment =>
                comment.id === commentId
                    ? { ...comment, edit_mode: value }
                    : comment
            )
        );
    };

    // Function to handle deleting a comment by ID using form data
    function handleDeleteComment(postId, commentId, csrf_token) {
        // Find the post to delete

        const formData = new FormData();
        formData.append('post_id', postId);
        formData.append('comment_index', commentId);
        formData.append('csrf_token', csrf_token);

        fetch('/delete-comment', {
            method: 'POST',
            credentials: 'include',
            body: formData
        })
        .then(res => {
            if (!res.ok) throw new Error('Failed to delete comment');
            // If successful, remove post from state
            setComments(prevComments => prevComments.filter(c => c.id !== commentId));
        })
        .catch(err => {
            // setError(`Delete failed: ${err.message}`);
            console.log(`Delete failed: ${err.message}`);
        });
    }

    return (
        <div>
            {comments && comments.length > 0 && (
                comments.map((comment, idx) => (
                    <div key={idx}>
                        {comment.edit_mode
                            ? (
                                <EditComment
                                    comment={comment}
                                    post_id={post._id}
                                    current_user={props.current_user}
                                    get_cookie={props.get_cookie}
                                    edit={handleEdit}
                                    delete={handleDeleteComment}
                                />
                            ) : (
                                <ViewComment
                                    comment={comment}
                                    post_id={post._id}
                                    current_user={props.current_user}
                                    get_cookie={props.get_cookie}
                                    edit={handleEdit}
                                    delete={handleDeleteComment}
                                />
                            )
                        }
                    </div>
                ))
            )}
        </div>
    );
}

export default Comments;