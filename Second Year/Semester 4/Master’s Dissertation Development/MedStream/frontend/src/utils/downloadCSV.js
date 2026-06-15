export function downloadCSV(filename, rows) {
  const processRow = (row) =>
    row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(",")

  const csvContent = rows.map(processRow).join("\n")

  const blob = new Blob([csvContent], {type: "text/csv;charset=utf-8;"})
  const url = URL.createObjectURL(blob)

  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", filename)
  link.click()
}