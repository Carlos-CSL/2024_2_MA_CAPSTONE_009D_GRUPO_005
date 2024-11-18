// Manejar el envío de comentarios
document.getElementById('commentForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const commentText = document.getElementById('commentText').value.trim();
    const productoId = document.getElementById('commentForm').dataset.productoId;
    if (commentText) {
        fetch(`/producto/${productoId}/comentar/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ texto: commentText })
        })
        .then(response => response.json())
        .then(data => {
            if (data.id) {
                const commentList = document.getElementById('commentsList');
                const newComment = document.createElement('div');
                newComment.id = `comentario-${data.id}`;
                newComment.classList.add('comment');
                newComment.innerHTML = `
                    <p class="username">${data.usuario}</p>
                    <p class="timestamp">${data.fecha}</p>
                    <p>${data.texto}</p>
                    ${data.is_admin ? `<button onclick="eliminarComentario(${data.id})" class="btn btn-danger btn-sm">Eliminar</button>` : ''}
                `;
                commentList.appendChild(newComment);
                document.getElementById('commentText').value = '';
            } else {
                alert(data.error || "Error al agregar el comentario.");
            }
        })
        .catch(error => console.error('Error:', error));
    }
});

// Manejar la eliminación de comentarios
function eliminarComentario(comentarioId) {
    fetch(`/comentario/${comentarioId}/eliminar/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById(`comentario-${comentarioId}`).remove();
        } else {
            alert("No tienes permiso para eliminar este comentario.");
        }
    })
    .catch(error => console.error('Error:', error));
}

// Obtener CSRF token de manera reutilizable
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}
