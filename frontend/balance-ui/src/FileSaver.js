try {
  if (window.showSaveFilePicker) {
    // Native save dialog (Chrome/Edge/Opera)
    const handle = await window.showSaveFilePicker({
      suggestedName: fileName,
      types: [
        {
          description: "Excel Files",
          accept: {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
              ".xlsx",
            ],
          },
        },
      ],
    });

    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
  } else {
    // Fallback for Firefox, Safari, etc.
    saveAs(blob, fileName);
  }
} catch (err) {
  console.error("Save canceled or failed:", err);
}
