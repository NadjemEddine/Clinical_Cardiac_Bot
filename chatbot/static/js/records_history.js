    $(document).ready(function() {
        $('#recordsTable').DataTable({
            responsive: true,
            order: [[0, 'desc']], // Sort by date (newest first)
            language: {
                search: "Search records:",
                lengthMenu: "Show _MENU_ records per page",
                info: "Showing _START_ to _END_ of _TOTAL_ records",
                emptyTable: "No records available"
            },
            columnDefs: [
                { responsivePriority: 1, targets: 0 }, // Date is most important
                { responsivePriority: 2, targets: 10 }, // Actions column is second most important
                { responsivePriority: 3, targets: 6 }, // Glucose level
                { responsivePriority: 4, targets: 7 } // Systolic BP
            ]
        });
    });