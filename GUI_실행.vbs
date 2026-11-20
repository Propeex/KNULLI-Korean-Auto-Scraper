' Double-click for GUI launch without a console window.
Option Explicit
Dim shell, fs, base, target
Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
base = fs.GetParentFolderName(WScript.ScriptFullName)
target = Chr(34) & fs.BuildPath(base,"GUI_실행.pyw") & Chr(34)
shell.CurrentDirectory = base
shell.Run "pyw -3 " & target, 0, False
