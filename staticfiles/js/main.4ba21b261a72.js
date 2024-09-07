// Search function
function filterTable() {
    var input, filter, table, tr, td, i, j, txtValue;
    input = document.getElementById("searchInput");
    filter = input.value.toUpperCase();
    table = document.getElementById("timeEntriesTable");
    tr = table.getElementsByTagName("tr");

    // Loop through all rows, and hide those that don't match the search query
    for (i = 1; i < tr.length; i++) {
        tr[i].style.display = "none"; // Initially hide all rows

        td = tr[i].getElementsByTagName("td");
        for (j = 0; j < td.length; j++) {
            if (td[j]) {
                txtValue = td[j].textContent || td[j].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    // If a match is found, show the entire group of rows that belong to this entry
                    showAllRowsInGroup(tr, i);
                    break;
                }
            }
        }
    }
}

// Function to show all rows in the group
function showAllRowsInGroup(tr, rowIndex) {
    var rowspan = parseInt(tr[rowIndex].getAttribute("rowspan")) || 1;
    
    // Show the current row
    tr[rowIndex].style.display = "";

    // Show subsequent rows that belong to the same group
    for (var k = 1; k < rowspan; k++) {
        if (tr[rowIndex + k]) {
            tr[rowIndex + k].style.display = "";
        }
    }
}
