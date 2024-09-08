"""
InterLivre, audiobook splicer
Copyright (C) 2024 VimHalen
See LICENSE for license information.
InterLivreApp@gmail.com
"""

import wx
import wx.html
from pubsub import pub
import re
from os.path import isdir
from appinfo import *
from webbrowser import open as web_open


class ILView:
    def __init__(self, appName):
        self.app = wx.App(False)
        self.app.SetAppName(appName)
        self.frame = ILFrame(None, appName)
        self.app.SetTopWindow(self.frame)

    def Start(self):
        self.app.MainLoop()


class ILFrame(wx.Frame):
    """InterLivre Frame"""
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent=parent, title=title, size=(400, 250),
                          style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.title = title
        self.InitMenus()
        self.book = ILBookView(self, title)

        self.progress = 0
        self.statusMsg = ""
        self.prgDlg = None

        self.windowSizer = wx.BoxSizer()
        self.windowSizer.Add(self.book, 1, wx.ALL | wx.EXPAND, 4)
        self.SetSizerAndFit(self.windowSizer)
        self.Show(True)

    def InitMenus(self):
        # Set up App/File Menu
        fileMenu = wx.Menu()
        aboutItem = fileMenu.Append(wx.ID_ABOUT, "&About", "Author: VimHalen, 2024")
        fileMenu.AppendSeparator()
        exitItem = fileMenu.Append(wx.ID_EXIT, "E&xit", f"Terminate {self.title}")
        closeItem = fileMenu.Append(wx.ID_CLOSE, f"Close", f"Terminate {self.title}")
        # Set up menu bar
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu, "&File")
        self.SetMenuBar(menuBar)
        # Set events
        self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
        self.Bind(wx.EVT_MENU, self.OnExit, exitItem)
        self.Bind(wx.EVT_MENU, self.OnExit, closeItem)

    def OnAbout(self, e):
        dlg = ILAboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, e):
        self.Close(False)

    def StartProgress(self):
        self.prgDlg = wx.ProgressDialog("Interleaving audiobooks", self.statusMsg, parent=self,
                                        style=0 | wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ELAPSED_TIME)
        self.prgDlg.Fit()

    def EndProgress(self, userCancelled):
        self.prgDlg.Destroy()
        if not userCancelled:
            dlg = wx.MessageDialog(None, "Interleaved audiobook is ready",
                                   "Success!", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

    def UpdateProgressStatus(self, progress, statusMsg):
        self.progress = progress
        self.statusMsg = statusMsg
        wx.MilliSleep(50)
        wx.Yield()
        keepGoing, _ = self.prgDlg.Update(self.progress, self.statusMsg)
        return not keepGoing

    def IsProgressCancelled(self):
        return self.prgDlg.WasCancelled()


class ILBookView(wx.Simplebook):
    def __init__(self, parent, title):
        wx.Simplebook.__init__(self, parent)
        self.title = title

        # Create Pages
        dirPage = ILPage(self, "ILDirSelectPage", self.OnNextPage, self.OnPrevPage,
                              isFirstPage=True, headerText="Choose folders containing audio files to interleave")
        reorderPage = ILPage(self, "ILFilesFoundPage", self.OnNextPage, self.OnPrevPage, headerText="Files found")
        audioPage = ILPage(self, "ILAudioSettingsPage", self.OnNextPage, self.OnPrevPage, headerText="Output and segmentation settings", isLastPage=True)
        self.AddPage(dirPage, "Choose folders")
        self.AddPage(reorderPage, "Confirm files")
        self.AddPage(audioPage, "Select output format")

        # Sizer
        self.windowSizer = wx.BoxSizer()
        self.windowSizer.Add(dirPage, 1, wx.ALL | wx.EXPAND, 4)
        self.SetSizerAndFit(self.windowSizer)

    def OnNextPage(self, e):
        pageIdx = self.GetSelection()
        nextPage = pageIdx + 1
        if nextPage < self.GetPageCount():
            if self.GetPage(pageIdx).Submit() == wx.ID_OK:
                self.ChangeSelection(nextPage)
        elif pageIdx == (self.GetPageCount() - 1):
            if self.GetPage(pageIdx).Submit() == wx.ID_OK:
                self.ChangeSelection(0)
                self.Reset()

    def OnPrevPage(self, e):
        pageIdx = self.GetSelection() - 1
        if pageIdx >= 0:
            self.ChangeSelection(pageIdx)

    def Reset(self):
        for i in range(0, self.GetPageCount()):
            self.GetPage(i).Reset()


class ILPage(wx.Panel):
    def __init__(self, parent, pageType, onNext, onPrev, isFirstPage=False, isLastPage=False, headerText=""):
        wx.Panel.__init__(self, parent)

        # Create widgets
        headerLabel = wx.StaticText(self, wx.ID_ANY, headerText)

        self.pageContents = None
        if pageType == "ILDirSelectPage":
            self.pageContents = ILDirSelectPage(self)
        elif pageType == "ILFilesFoundPage":
            self.pageContents = ILFilesFoundPage(self)
        elif pageType == "ILAudioSettingsPage":
            self.pageContents = ILAudioSettingsPage(self)
        else:
            pass

        # Back button
        self.backBtn = wx.Button(self, wx.ID_ANY, "< Back")
        self.backBtn.Bind(wx.EVT_BUTTON, onPrev)
        if isFirstPage:
            self.backBtn.Hide()

        # Next button
        nextBtnText = "Run" if isLastPage else "Next >"
        self.nextBtn = wx.Button(self, wx.ID_ANY, nextBtnText)
        self.nextBtn.Bind(wx.EVT_BUTTON, onNext)
        if issubclass(type(self.pageContents), ILForm):
            if self.pageContents.hasMandatoryFields:
                self.nextBtn.Disable()
                pub.subscribe(self.OnEnableNextButton, self.pageContents.readyMsg)

        # Layout buttons
        self.btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btnSizer.Add(self.backBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 2)
        self.btnSizer.Add(self.nextBtn, 0, wx.ALL | wx.ALIGN_BOTTOM, 2)

        # Layout frame
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(headerLabel, 0, wx.ALL | wx.CENTER, 2)
        self.vbox.Add(self.pageContents, 1, wx.ALL | wx.EXPAND, 2)
        self.vbox.Add(self.btnSizer, 0, wx.ALL | wx.ALIGN_RIGHT, 6)

        # Sizer
        self.SetSizer(self.vbox)
        self.SetAutoLayout(1)
        self.vbox.Fit(self)
        self.SetSizerAndFit(self.vbox)

    def OnEnableNextButton(self, isReady):
        self.nextBtn.Enable(isReady)

    def Submit(self):
        res = wx.ID_OK
        if issubclass(type(self.pageContents), ILForm):
            res = self.pageContents.Submit()
        return res

    def Reset(self):
        if issubclass(type(self.pageContents), ILForm):
            self.pageContents.Reset()


class ILForm:
    def __init__(self, hasMandatoryFields=False, readyMsg=""):
        self.hasMandatoryFields = hasMandatoryFields
        self.readyMsg = readyMsg

    def Submit(self):
        raise NotImplementedError()

    def Reset(self):
        raise NotImplementedError()


class ILDirSelectPage(wx.Panel, ILForm):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        ILForm.__init__(self, hasMandatoryFields=True, readyMsg="PathsReadyChanged")

        # Create widgets
        self.book1Input = ILDirWidget(self, "Src1", "Book 1")
        self.book2Input = ILDirWidget(self, "Src2", "Book 2")
        self.outputDirectory = ILDirWidget(self, "Dst", "Output")
        self.fname = ILTextWidget(self, "DstName", "Output file name prefix")
        self.isReady = False
        pub.subscribe(self.OnDirChanging, "DirWidgetChanging")

        # Sizer
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.book1Input, 0, wx.ALL | wx.EXPAND, 2)
        self.vbox.Add(self.book2Input, 0, wx.ALL | wx.EXPAND, 2)
        self.vbox.Add(self.outputDirectory, 0, wx.ALL | wx.EXPAND, 2)
        self.vbox.Add(self.fname, 0, wx.ALL | wx.EXPAND, 2)

        self.SetSizer(self.vbox)
        self.SetAutoLayout(1)
        self.vbox.Fit(self)
        self.SetSizerAndFit(self.vbox)

    def Submit(self):
        if not isdir(self.book1Input.GetValue()):
            return self.ShowError("Book 1 entry is not a folder", f"Couldn't find \"{self.book1Input.GetValue()}\"")
        if not isdir(self.book2Input.GetValue()):
            return self.ShowError("Book 2 entry is not a folder", f"Couldn't find \"{self.book2Input.GetValue()}\"")
        if not isdir(self.outputDirectory.GetValue()):
            return self.ShowError("Output entry is not a folder",
                                  f"Couldn't find \"{self.outputDirectory.GetValue()}\" folder")
        strPrefix = self.fname.pathCtrl.GetLabelText()
        if re.compile('[\\\\/\*:\?"<>\|]').search(strPrefix):
            return self.ShowError("Invalid file name",
                                  "Try removing special characters or punctuation from the output file name")
        return wx.ID_OK

    def Reset(self):
        self.book1Input.Clear()
        self.book2Input.Clear()
        self.outputDirectory.Clear()
        self.fname.Clear()

    def ShowError(self, msgTitle, msg):
        dlg = wx.MessageDialog(None, msg, msgTitle, wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()
        return wx.ID_CANCEL

    def OnDirChanging(self):
        src1Ready = self.book1Input.GetValue() != ""
        src2Ready = self.book2Input.GetValue() != ""
        dstReady = self.outputDirectory.GetValue() != ""
        fnameReady = self.fname.GetValue() != ""
        pathsReady = src1Ready and src2Ready and dstReady and fnameReady
        if self.isReady != pathsReady:
            self.isReady = pathsReady
            pub.sendMessage("PathsReadyChanged", isReady=self.isReady)

class ILFilesFoundPage(wx.Panel, ILForm):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        ILForm.__init__(self, hasMandatoryFields=False)
        self.files = [[], []]
        self.filesDisplay = [[], []]
        self.dirty = False

        # Widgets
        book1Header = wx.StaticText(self, wx.ID_ANY, "Book 1")
        book2Header = wx.StaticText(self, wx.ID_ANY, "Book 2")
        self.book1 = wx.RearrangeList(self, items=self.filesDisplay[0])
        self.book2 = wx.RearrangeList(self, items=self.filesDisplay[1])
        noteText = wx.StaticText(self, wx.ID_ANY, "Note, selected files in the two lists will be paired up in sequence")
        font = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.LIGHT)
        noteText.SetFont(font)

        # Bindings
        pub.subscribe(self.OnFilesChanged, "SrcFileListChanged")

        # Sizer
        grid = wx.FlexGridSizer(2, 3, 2)
        grid.AddGrowableRow(1, 1)
        grid.SetFlexibleDirection(wx.VERTICAL)
        grid.AddGrowableCol(0, 1)
        grid.AddGrowableCol(1, 1)
        grid.Add(book1Header, flag=wx.ALIGN_CENTER)
        grid.Add(book2Header, flag=wx.ALIGN_CENTER)
        grid.Add(self.book1, flag=wx.EXPAND)
        grid.Add(self.book2, flag=wx.EXPAND)
        grid.Add(noteText, flag=wx.ALIGN_LEFT)
        self.SetAutoLayout(1)
        self.SetSizerAndFit(grid)
        self.minWidth = (self.GetMinWidth() / 2)

    def CollapseStrings(self, filelist):
        res = []
        for f in filelist:
            if len(f) < 5:
                # 5 always fits
                continue
            # Begin deleting chars from the middle and proceed outwards
            fLo = f[:int(len(f)/2)-1]
            fHi = f[int(len(f)/2)+2:]
            while self.GetTextExtent(fLo + "..." + fHi)[0] >= self.minWidth:
                fLo = fLo[0:-1]
                fHi = fHi[1:]
            truncLen = len(fLo) + len(fHi) + 3
            if truncLen != len(f):
                res.append(fLo + "..." + fHi)
            else:
                res.append(f)
        return res

    def OnFilesChanged(self, files):
        if len(files) == 2:
            self.files = files
            self.filesDisplay[0] = self.CollapseStrings(self.files[0])
            self.filesDisplay[1] = self.CollapseStrings(self.files[1])
            self.book1.Set(self.filesDisplay[0])
            self.book2.Set(self.filesDisplay[1])
            self.book1.SetCheckedItems(range(0, len(self.filesDisplay[0])))
            self.book2.SetCheckedItems(range(0, len(self.filesDisplay[1])))

    def Submit(self):
        fileList = [[self.files[0][i] for i in self.book1.GetCheckedItems()],
                    [self.files[1][i] for i in self.book1.GetCheckedItems()]]
        if len(fileList[0]) != len(fileList[1]):
            dlg = wx.MessageDialog(None, "Different number of files selected for Books 1 and 2.",
                                   "File count error", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return wx.ID_CANCEL
        pub.sendMessage("SrcFilesSelectedChanging", files=fileList)
        return wx.ID_OK

    def Reset(self):
        self.book1.Clear()
        self.book2.Clear()


class ILAudioSettingsPage(wx.Panel, ILForm):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        ILForm.__init__(self, hasMandatoryFields=False)
        self.sampleRates = ["48000", "44100", "16000"]
        self.fileFormats = ["wav", "mp3"]

        # Widgets
        # Audio format
        sampleRateLabel = wx.StaticText(self, -1, "Sample rate")
        fileFormatLabel = wx.StaticText(self, -1, "File format")
        self.sampleRateChoice = wx.Choice(self, choices=self.sampleRates)
        self.fileFormatChoice = wx.Choice(self, choices=self.fileFormats)
        self.sampleRateChoice.SetSelection(0)
        self.fileFormatChoice.SetSelection(0)

        # Segments
        segRangeLabel = wx.StaticText(self, wx.ID_ANY, "Number of seconds to wait before switching between recordings")
        segMinLabel = wx.StaticText(self, wx.ID_ANY, "Min")
        segMaxLabel = wx.StaticText(self, wx.ID_ANY, "Max")
        self.segMinSpinCtrl = wx.SpinCtrl(self, wx.ID_ANY)
        self.segMaxSpinCtrl = wx.SpinCtrl(self, wx.ID_ANY)
        self.segMinSpinCtrl.SetRange(1, 999)
        self.segMaxSpinCtrl.SetRange(5, 1000)
        self.segMinSpinCtrl.SetValue(5)
        self.segMaxSpinCtrl.SetValue(18)

        # Write to disk
        self.writeSegmentsChk = wx.CheckBox(self, wx.ID_ANY, label="Write speech segments to disk as 48k wav files")

        # Bindings
        self.sampleRateChoice.Bind(wx.EVT_CHOICE, self.OnSampleRateChosen)
        self.fileFormatChoice.Bind(wx.EVT_CHOICE, self.OnFileFormatChosen)
        self.segMinSpinCtrl.Bind(wx.EVT_SPINCTRL, self.OnMinSegmentChanged)
        self.segMaxSpinCtrl.Bind(wx.EVT_SPINCTRL, self.OnMaxSegmentChanged)
        self.writeSegmentsChk.Bind(wx.EVT_CHECKBOX, self.OnWriteBoxToggled)

        # Subscribe
        pub.subscribe(self.OnSegmentRangeChanged, "SegmentRangeChanged")
        pub.subscribe(self.OnWriteSegmentsChanged, "WriteSegmentsChanged")

        # Sizers
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(segMinLabel, 0, wx.ALL | wx.CENTER, 2)
        hbox.Add(self.segMinSpinCtrl, 0, wx.ALL, 2)
        hbox.Add(segMaxLabel, 0, wx.ALL | wx.CENTER, 2)
        hbox.Add(self.segMaxSpinCtrl, 0, wx.ALL, 2)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(sampleRateLabel, 0, wx.ALL | wx.EXPAND, 2)
        vbox.Add(self.sampleRateChoice, 0, wx.ALL | wx.EXPAND, 2)
        vbox.Add(fileFormatLabel, 0, wx.ALL | wx.EXPAND, 2)
        vbox.Add(self.fileFormatChoice, 0, wx.ALL | wx.EXPAND, 2)
        vbox.AddSpacer(8)
        vbox.Add(segRangeLabel, 0, wx.ALL | wx.EXPAND, 2)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 2)
        vbox.AddSpacer(8)
        vbox.Add(self.writeSegmentsChk, 0, wx.ALL | wx.EXPAND, 2)

        self.SetAutoLayout(1)
        self.SetSizerAndFit(vbox)

    def Submit(self):
        dlg = wx.MessageDialog(None, "This could take a long time...", "Ready to combine books?", wx.OK | wx.CANCEL)
        res = dlg.ShowModal()
        if res == wx.ID_OK:
            pub.sendMessage("Convert")
        dlg.Destroy()
        return res

    def OnSampleRateChosen(self, e):
        i = self.sampleRateChoice.GetCurrentSelection()
        pub.sendMessage("DstSampleRateChanging", sample_rate=int(self.sampleRates[i]))

    def OnFileFormatChosen(self, e):
        i = self.fileFormatChoice.GetCurrentSelection()
        pub.sendMessage("DstFileFormatChanging", file_format=self.fileFormats[i])

    def OnSegmentRangeChanged(self, srange):
        self.segMinSpinCtrl.SetValue(srange[0])
        self.segMaxSpinCtrl.SetValue(srange[1])

    def OnMinSegmentChanged(self, e):
        sctrlMax = self.segMaxSpinCtrl.GetValue()
        if self.segMinSpinCtrl.GetValue() >= sctrlMax:
            self.segMinSpinCtrl.SetValue(sctrlMax - 1)
        pub.sendMessage("SegmentRangeChanging", srange=[self.segMinSpinCtrl.GetValue(), sctrlMax])

    def OnMaxSegmentChanged(self, e):
        sctrlMin = self.segMinSpinCtrl.GetValue()
        if self.segMaxSpinCtrl.GetValue() <= sctrlMin:
            self.segMaxSpinCtrl.SetValue(sctrlMin + 1)
        pub.sendMessage("SegmentRangeChanging", srange=[sctrlMin, self.segMaxSpinCtrl.GetValue()])

    def OnWriteSegmentsChanged(self, should_write_segments):
        self.writeSegmentsChk.SetValue(should_write_segments)

    def OnWriteBoxToggled(self, e):
        chkState = self.writeSegmentsChk.GetValue()
        pub.sendMessage("WriteSegmentsChanging", should_write_segments=chkState)

    def Reset(self):
        self.sampleRateChoice.SetSelection(0)
        self.fileFormatChoice.SetSelection(0)
        pub.sendMessage("DstSampleRateChanging", sample_rate=int(self.sampleRates[0]))
        pub.sendMessage("DstFileFormatChanging", file_format=self.fileFormats[0])


class ILDirWidget(wx.Panel):
    def __init__(self, parent, title, displayStr):
        wx.Panel.__init__(self, parent)
        self.title = title
        self.margin = 2

        # Widgets
        self.displayStr = wx.StaticText(self, wx.ID_ANY, f"{displayStr} folder")
        self.pathCtrl = wx.TextCtrl(self)
        exampleStr = "/Users/CurrentUser/Audiobooks/Public_domain/InterLivre/Source/Bram_Stoker/Dracula/English/mono"
        self.pathCtrl.SetInitialSize(
            self.pathCtrl.GetSizeFromTextSize(
                self.pathCtrl.GetTextExtent(exampleStr)))
        self.dirButton = wx.Button(self, wx.ID_ANY, "Browse...")

        # Sizers
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox.Add(self.pathCtrl, 1, wx.EXPAND | wx.ALL, self.margin)
        self.hbox.Add(self.dirButton, 0, wx.EXPAND | wx.ALL, self.margin)
        self.vbox.Add(self.displayStr, 0, wx.EXPAND | wx.LEFT, self.margin + 2)
        self.vbox.Add(self.hbox, 0, wx.EXPAND | wx.ALL, self.margin)
        self.SetSizer(self.vbox)
        self.SetAutoLayout(1)
        self.vbox.Fit(self)

        # Bindings
        self.dirButton.Bind(wx.EVT_BUTTON, self.OnDir)
        self.pathCtrl.Bind(wx.EVT_TEXT, self.OnText)
        pub.subscribe(self.UpdateText, f"{self.title}Changed")

    def OnDir(self, event):
        dlg = wx.DirDialog(self, "Choose a folder", style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.pathCtrl.SetValue(path)
            pub.sendMessage(f"{self.title}Changing", dir_str=path)
            pub.sendMessage(f"DirWidgetChanging")
        dlg.Destroy()

    def OnText(self, event):
        pub.sendMessage(f"{self.title}Changing", dir_str=event.EventObject.Value)
        pub.sendMessage(f"DirWidgetChanging")

    def UpdateText(self, path):
        self.pathCtrl.SetValue(path)

    def Clear(self):
        self.pathCtrl.Clear()
        pub.sendMessage(f"{self.title}Changing", dir_str="")
        pub.sendMessage(f"DirWidgetChanging")

    def GetValue(self):
        return self.pathCtrl.GetValue()


class ILTextWidget(wx.Panel):
    def __init__(self, parent, title, displayStr):
        wx.Panel.__init__(self, parent)
        self.title = title
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.margin = 4
        self.displayStr = wx.StaticText(self, wx.ID_ANY, displayStr)
        self.pathCtrl = wx.TextCtrl(self)
        self.vbox.Add(self.displayStr, 0, wx.EXPAND | wx.LEFT, self.margin)
        self.vbox.Add(self.pathCtrl, 0, wx.EXPAND | wx.ALL, self.margin)
        self.SetSizer(self.vbox)
        self.SetAutoLayout(1)
        self.vbox.Fit(self)
        self.pathCtrl.Bind(wx.EVT_TEXT, self.OnText)
        pub.subscribe(self.UpdateText, f"{self.title}Changed")

    def OnText(self, event):
        pub.sendMessage(f"{self.title}Changing", name=event.EventObject.Value)
        pub.sendMessage(f"DirWidgetChanging")

    def UpdateText(self, text):
        self.pathCtrl.SetValue(text)

    def Clear(self):
        self.pathCtrl.Clear()
        pub.sendMessage(f"{self.title}Changing", name="")
        pub.sendMessage(f"DirWidgetChanging")

    def GetValue(self):
        return self.pathCtrl.GetValue()


class ILAboutDialog(wx.Dialog):
    aboutText = f"""
    <html>
    <body>
    <center>
    <h1>{APP_NAME}</h1>
    <p>{VERSION}</p>
    <p><b>{APP_NAME}</b> is a short hobby project I wrote in Summer, 2024 to splice together English and French versions
    of audiobooks.</p>
    <p>I hope it can be helpful to others. However, be warned, I wrote this quickly and tested
    it lightly... use it at your own risk!</p>
    <p><b>{APP_NAME}</b> Copyright (c) {COPYRIGHT} <b>{AUTHOR}</b></p>
    <p>{CONTACT}</p>
    <hr>
    <p><font size="-1"> This program comes with ABSOLUTELY NO WARRANTY and is released under the GNU General Public
    License, version 3: <a href={LICENSE_URL}>{LICENSE_URL}</a>.
    Please see <i>{LICENSE_FILE}</i>, distributed with <b>{APP_NAME}</b>, for details and license information.
    </font>
    </p>
    <hr>
    <p><font size="-1"><b>{APP_NAME}</b> is written in Python and uses the following tools/libraries, which have their 
    own licenses available at the links below and reproduced in the <i>{DEPENDENCY_LICENSE_INFO}</i> file, distributed
    with <b>{APP_NAME}</b>:</font></p>
    <p><font size="-1">%s</font></p>
    </center>
    </body>
    </html>
    """
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "About InterLivre")
        html = ILHtmlWindow(self, -1)
        if "gtk2" in wx.PlatformInfo or "gtk3" in wx.PlatformInfo:
            html.SetStandardFonts()
        txt = self.aboutText % self.GetDependencyLicenseHtml(DEPENDENCY_URLS)
        html.SetPage(txt)
        ir = html.GetInternalRepresentation()
        html.SetSize((ir.GetWidth()+25, ir.GetHeight()+25))
        self.SetClientSize(html.GetSize())
        self.CentreOnParent(wx.BOTH)

    def GetDependencyLicenseHtml(self, depInfo):
        res = "<table>"
        for dep, urls in depInfo.items():
            depStr = f"""
            <tr>
            <td><a href={urls['home']} style="color: black">{dep}</a>:</td>
            <td><a href={urls['license']}>{urls['license']}</a></td>
            </tr>
            """
            res += depStr
        res += "</table>"
        return res


class ILHtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, id):
        wx.html.HtmlWindow.__init__(self, parent, id, size=(420, -1), style=wx.NO_FULL_REPAINT_ON_RESIZE)
        if "gtk2" in wx.PlatformInfo or "gtk3" in wx.PlatformInfo:
            self.SetStandardFonts()

    def OnLinkClicked(self, linkInfo):
        web_open(linkInfo.GetHref())
