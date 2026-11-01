Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")
userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
pywPath = userProfile & "\AppData\Local\Programs\Python\Python311\pythonw.exe"
If Not fso.FileExists(pywPath) Then
    pywPath = "pythonw.exe"
End If

botPath = scriptDir & "\bot.py"
cmdLine = """" & pywPath & """ -u """ & botPath & """"

Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set objProcess = objWMIService.Get("Win32_Process")
errReturn = objProcess.Create(cmdLine, scriptDir, Null, processID)

Set objProcess = Nothing
Set objWMIService = Nothing
Set WshShell = Nothing
Set fso = Nothing
