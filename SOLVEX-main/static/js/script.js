document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const tableBody = document.getElementById("ticketTableBody");
    const rows = Array.from(tableBody.getElementsByTagName("tr"));
    const ticketForm = document.getElementById("ticketForm");

    // Filtro de búsqueda
    searchInput.addEventListener("input", function () {
        const searchTerm = searchInput.value.toLowerCase();
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            row.style.display = text.includes(searchTerm) ? "" : "none";
        });
    });

    // Envío del formulario con AJAX
    ticketForm.addEventListener("submit", function (event) {
        event.preventDefault(); // Evita recargar la página

        const formData = new FormData(ticketForm);
        fetch(ticketForm.action, {
            method: "POST",
            body: formData,
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(response => {
            if (response.status === 204) {
                location.reload(); // Recarga la página
            }
            return response.json();
        })
        .then(data => {
            if (data.id) {
                const newRow = document.createElement("tr");
                newRow.innerHTML = `
                    <td>${data.id}</td>
                    <td>${data.motivo}</td>
                    <td>${data.tipo_soporte}</td>
                    <td>${data.estado}</td>
                    <td>${data.prioridad}</td>
                    <td>${data.fecha_creacion}</td>
                `;
                tableBody.insertBefore(newRow, tableBody.firstChild);
                ticketForm.reset();
            }
        })
        .catch(error => console.error("Error al enviar el formulario:", error));
    });
});
