; ARCA Facturador NSIS Installer Script
; Requires NSIS 3.0+

!define PRODUCT_NAME "ARCA Facturador"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "ARCA Facturador"
!define PRODUCT_WEB_SITE "https://github.com/user/arca-facturador"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\ARCA_Facturador.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma
RequestExecutionLevel admin

!include "MUI2.nsh"
!include "FileFunc.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\resources\icon.ico"
!define MUI_UNICON "..\resources\icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "English"

Section "Instalar ARCA Facturador" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Main executable
    File "..\dist\ARCA_Facturador.exe"
    File "..\config.yaml"
    File "..\.env.example"

    ; Resources
    SetOutPath "$INSTDIR\resources"
    File /r "..\resources\*.*"

    ; Cert directory
    SetOutPath "$INSTDIR\certs"
    File "..\certs\*.*"

    ; Data directory
    SetOutPath "$INSTDIR\data"

    ; Create shortcuts
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\ARCA Facturador.lnk" "$INSTDIR\ARCA_Facturador.exe" "" "$INSTDIR\resources\icon.ico"
    CreateShortCut "$DESKTOP\ARCA Facturador.lnk" "$INSTDIR\ARCA_Facturador.exe" "" "$INSTDIR\resources\icon.ico"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Desinstalar.lnk" "$INSTDIR\uninst.exe"

    ; File association for .afip
    WriteRegStr HKCR ".afip" "" "ARCAFacturador.Document"
    WriteRegStr HKCR "ARCAFacturador.Document" "" "Documento ARCA Facturador"
    WriteRegStr HKCR "ARCAFacturador.Document\shell\open\command" "" '"$INSTDIR\ARCA_Facturador.exe" "%1"'

    ; Registry for uninstall
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\ARCA_Facturador.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninst.exe"

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "EstimatedSize" "$0"

SectionEnd

Section "Uninstall"
    ; Remove shortcuts
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\ARCA Facturador.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\Desinstalar.lnk"
    RmDir "$SMPROGRAMS\${PRODUCT_NAME}"

    Delete "$DESKTOP\ARCA Facturador.lnk"

    ; Remove registry
    DeleteRegKey HKCR ".afip"
    DeleteRegKey HKCR "ARCAFacturador.Document"
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}"

    ; Remove files (preserve data)
    Delete "$INSTDIR\ARCA_Facturador.exe"
    Delete "$INSTDIR\uninst.exe"
    Delete "$INSTDIR\config.yaml"
    Delete "$INSTDIR\.env.example"
    RmDir /r "$INSTDIR\resources"
    RmDir /r "$INSTDIR\certs"
    RmDir "$INSTDIR"

SectionEnd
