; My First NSIS Installer Script

; Includes
!include "MUI2.nsh" ; Modern User Interface

; Defines
; Installer Settings
!ifndef NAME
  !define NAME "MyApplication"
!endif
!ifndef VERSION
  !define VERSION "1.0"
!endif
!ifndef BUILD_DIR
  !error "BUILD_DIR must be defined"
!endif
!ifndef MAIN_EXE_NAME
  !define MAIN_EXE_NAME "MyApplication.exe"
!endif
!ifndef OUT_DIR
  !define OUT_DIR "$EXEDIR"
!endif
!define APP_DIR "${NAME}"

Name "${NAME} ${VERSION}"
OutFile "${OUT_DIR}\${NAME}_Installer_${VERSION}.exe"
InstallDir "$PROGRAMFILES\${APP_DIR}"
RequestExecutionLevel admin

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Sections (Installation Logic)
Section "Install"
    SetOutPath "$INSTDIR"
    ; Install all files from the build directory
    File /r "${BUILD_DIR}\*.*"
    
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${NAME}" "DisplayName" "${NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${NAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteUninstaller "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\${NAME}.lnk" "$INSTDIR\${MAIN_EXE_NAME}"
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove the installation directory recursively
    RMDir /r "$INSTDIR"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${NAME}"
    Delete "$DESKTOP\${NAME}.lnk"
SectionEnd