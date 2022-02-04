import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import pydicom

#
# DICOM_Modify
#

class DICOM_Modify(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "DICOM_Modify"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["MikeTools"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Mike Bindschadler (Seattle Children's Hospital)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This modules allows modification of tags in DICOM volumes, either into another output directory, or in place.
This uses pydicom under the hood.  The existing DICOM file is loaded into a pydicom dataset, then tags are
modified using setattr(myDataSet, Tag, Value). If a tag you are modifying requires a list, indicate that
by enclosing the list elements, separated by commas, in square brackets.  For example "[1,2,3,4]". This
will be converted to a python list before being passed to pydicom. Otherwise, pydicom handles any needed
conversion between strings and numbers. 

Please note, this module does absolutely no checking that you are providing valid values or that
your modified DICOM files will be valid. The DICOM standard is extremely complex, and you should
only be modifying files using this tool if you know what you are doing!
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Mike Bindschadler with support from Seattle Children's Hospital.
"""

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#

def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # DICOM_Modify1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='DICOM_Modify',
    sampleName='DICOM_Modify1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'DICOM_Modify1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='DICOM_Modify1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums = 'SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='DICOM_Modify1'
  )

  # DICOM_Modify2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='DICOM_Modify',
    sampleName='DICOM_Modify2',
    thumbnailFileName=os.path.join(iconsPath, 'DICOM_Modify2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='DICOM_Modify2.nrrd',
    checksums = 'SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='DICOM_Modify2'
  )

#
# DICOM_ModifyWidget
#

class DICOM_ModifyWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/DICOM_Modify.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Force input selector to use the Open (rather than the "Save" dialog) and be restricted to files (not directories)
    self.ui.InputDICOMPathLineEdit.filters = ctk.ctkPathLineEdit.Readable + ctk.ctkPathLineEdit.Files

    # Force output directory selector to only allow directories as values (hide files, allow directories only)
    self.ui.OutputDICOMPathLineEdit.filters = ctk.ctkPathLineEdit.Dirs
    
    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = DICOM_ModifyLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)


    self.ui.ModifyAllPushButton.clicked.connect(self.onModifyAllPushButtonClick)
    self.ui.ModifySinglePushButton.clicked.connect(self.onModifySinglePushButtonClick)
    self.ui.OverwriteRadioButton.toggled.connect(self.onOverwriteRadioButtonClick)
    self.ui.OutputDirRadioButton.toggled.connect(self.onOutputDirRadioButtonClick)
    
    ''' I have removed any dependence on a parameter node for this module, because it is 
    so simple and I don't see a need for making it reloadable, it's really just for 
    active modifications.  However, if it is made more complicated in the future, it
    might be worth restoring the parameter node, in which case some of the template code 
    is helpful, so I'm just going to comment it out rather than delete it.  Look for
    PARAMNODE comments if you're looking to restore'''
    '''PARAMNODE
    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()'''

  def onModifyAllPushButtonClick(self):
    '''Triggers modifying all DICOM files in the directory of the selected input DICOM file'''
    logging.debug('Launching DICOM_Modify modify all...')
    # Get selected file path
    selectedFile = self.ui.InputDICOMPathLineEdit.currentPath
    logging.debug('Selected file: %s' % (selectedFile))
    # Validate that it is a DICOM file
    if not self.logic.isValidDICOMFile(selectedFile):
      slicer.util.warningDisplay('The selected input file is not a valid DICOM file!  Canceling...')
      logging.debug('Canceled modify all because selected file was not a valid DICOM file.')
      return
    # Gather all the files in that directory
    basePath, fileName = os.path.split(selectedFile)
    (_,_, files_to_modify) = next(os.walk(basePath))
    filePathsToModify = [os.path.join(basePath, fileName) for fileName in files_to_modify]
    logging.debug('Gathered %i files to modify.' % (len(filePathsToModify)))
    # Deterimine the output directory (i.e. same for overwrite, or specified other directory)
    outputDirectory = self.getOutputDirectory()
    if outputDirectory=='':
      slicer.util.warningDisplay('No selected output directory! Canceling...')
      return
    # Assemble output paths
    outputFilePaths = [os.path.join(outputDirectory, fileName) for fileName in files_to_modify]
    # Gather Tags to modify
    tagNumDict = self.gatherTagNumDict()
    tagNameDict = self.gatherTagNameDict()
    # TODO: Validate these tags before actually running any modification?
    # Run the modification
    for inputFilePath, outputFilePath in zip(filePathsToModify, outputFilePaths):
      successFlag, err = self.logic.modifyDicomFile(inputFilePath, outputFilePath, tagNameDict, tagNumDict)
      if not successFlag:
        logging.warning('DICOM file modification failed for %s'%inputFilePath)
        logging.warning('Error message: %s' % (str(err)))

  def onModifySinglePushButtonClick(self):
    '''Triggers modification of the single selected DICOM file'''
    logging.debug('Launching DICOM_Modify single file...')
    # Get selected file path
    selectedFile = self.ui.InputDICOMPathLineEdit.currentPath
    logging.debug('Selected file: %s' % (selectedFile))
    # Validate that it is a DICOM file
    if not self.logic.isValidDICOMFile(selectedFile):
      slicer.util.warningDisplay('The selected input file is not a valid DICOM file!  Canceling...')
      logging.debug('Canceled modify all because selected file was not a valid DICOM file.')
      return
    # Deterimine the output directory (i.e. same for overwrite, or specified other directory)
    outputDirectory = self.getOutputDirectory()
    if outputDirectory=='':
      slicer.util.warningDisplay('The selected output directory is empty! Canceling...')
      return
    _, selectedFileName = os.path.split(selectedFile)
    outputFilePath = os.path.join(outputDirectory, selectedFileName)
    # Gather Tags to modify
    tagNumDict = self.gatherTagNumDict()
    tagNameDict = self.gatherTagNameDict()
    # TODO: Validate these tags before actually running any modification?
    # Run the modification
    successFlag, err = self.logic.modifyDicomFile(selectedFile, outputFilePath, tagNameDict, tagNumDict)
    if not successFlag:
      logging.warning('DICOM file modification failed for %s'%selectedFile)
      logging.warning('Error message: %s' % (str(err)))
      raise err # may as well raise it, this was the only file we were trying for

  def getOutputDirectory(self):
    '''Determine output directory based on radio button selections'''
    if self.ui.OverwriteRadioButton.checked:
      # Overwrite in place, return the input directory as the output directory
      selectedFile = self.ui.InputDICOMPathLineEdit.currentPath
      outputDirectory = os.path.dirname(selectedFile)
    else:
      # Write modified files to a new directory, as specified
      outputDirectory = self.ui.OutputDICOMPathLineEdit.currentPath # is '' if not selected
    return outputDirectory
    
  def gatherTagNameDict(self):
    '''Gather tag names and new values from GUI into a dictionary'''
    tagNames = [getattr(self.ui,'TagName%i'%idx).text for idx in range(5)]
    tagValues = [getattr(self.ui,'TagNameVal%i'%idx).text for idx in range(5)]
    tagNameDict = {}
    for tagName, tagValue in zip(tagNames, tagValues):
      if tagName and tagValue: # only write if both are not ''
        tagNameDict[tagName] = tagValue
    return tagNameDict

  def gatherTagNumDict(self):
    '''Gather tag numbers and new values from GUI into a dictionary'''
    '''int('str', 16) works for conversion from normal DICOM specifiers to hex based int'''
    tagNums = [(getattr(self.ui,'TagNum_%i%i'%(r,0)).text, getattr(self.ui,'TagNum_%i%i'%(r,1)).text ) for r in range(5)]
    tagValues = [getattr(self.ui, 'TagNumVal_%i'%(r)).text for r in range(5)]
    tagValues = [self.logic.convertTagValueString(v) for v in tagValues] # 
    tagNumDict = {}
    for tagNumTup, tagValue in zip(tagNums, tagValues):
      if tagNumTup[0] and tagNumTup[1] and tagValue:
        # Interpret tag nums as hex-based integers
        tagNumKey = (int(tagNumTup[0], 16), int(tagNumTup[1], 16))
        tagNumDict[tagNumKey] = tagValue
    return tagNumDict

  def onOverwriteRadioButtonClick(self):
    '''Select overwrite radio button and unselect output directory radio button'''
    wasBlocked = self.ui.OverwriteRadioButton.blockSignals(True)
    self.ui.OverwriteRadioButton.checked = True
    self.ui.OverwriteRadioButton.blockSignals(wasBlocked)

    wasBlocked =  self.ui.OutputDirRadioButton.blockSignals(True)
    self.ui.OutputDirRadioButton.checked = False
    self.ui.OutputDirRadioButton.blockSignals(wasBlocked)

  def onOutputDirRadioButtonClick(self):
    '''Select output directory radio button and unselect overwrite radio button'''
    wasBlocked =  self.ui.OutputDirRadioButton.blockSignals(True)
    self.ui.OutputDirRadioButton.checked = True
    self.ui.OutputDirRadioButton.blockSignals(wasBlocked)
    
    wasBlocked = self.ui.OverwriteRadioButton.blockSignals(True)
    self.ui.OverwriteRadioButton.checked = False
    self.ui.OverwriteRadioButton.blockSignals(wasBlocked)

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    '''PARAMNODE
    # Make sure parameter node exists and observed
    self.initializeParameterNode()
    '''

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    '''PARAMNODE
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    '''

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    '''PARAMNODE
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)
    '''

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    '''PARAMNODE
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()
    '''
  '''PARAMNODE
  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
    self.ui.invertedOutputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolumeInverse"))
    self.ui.imageThresholdSliderWidget.value = float(self._parameterNode.GetParameter("Threshold"))
    self.ui.invertOutputCheckBox.checked = (self._parameterNode.GetParameter("Invert") == "true")

    # Update buttons states and tooltips
    if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
      self.ui.applyButton.toolTip = "Compute output volume"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input and output volume nodes"
      self.ui.applyButton.enabled = False

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
    self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
    self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
    self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.ui.invertedOutputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  '''

#
# DICOM_ModifyLogic
#

class DICOM_ModifyLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

  '''PARAMNODE
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "100.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")
  '''
  def convertTagValueString(self, tagValueString):
    """ Convert to list if in brackets, otherwise return unchanged
    """
    import re
    patt = re.compile("^\w*\[(.*)]\w*")
    m = patt.fullmatch(tagValueString)
    if m:
      # Split into a list of strings for multi-valued DICOM element
      values = m[1].split(',') # split list elements by commas
      tagValue = [v.strip() for v in values] # strip any extra whitespace around list elements
    else:
      # Not a multi-valued tag string, just return unmodified string (this is correct for numerical values as well)
      tagValue = tagValueString
    return tagValue

  def isValidDICOMFile(self, filePath):
    #TODO TODO write dicom validator here
    return True

  def modifyDicomFile(self, inputFilePath, outputFilePath, tagNameDict={}, tagNumDict={}):
    '''Do the actual modification'''
    try: 
      ds = pydicom.dcmread(inputFilePath)
      for tag, val in tagNumDict.items():
        ds[tag].value = val
      for tag, val in tagNameDict.items():
        setattr(ds, tag, val)
        # NOTE: ds[tag].value = val will work IFF ds already has tag, but throws error if it doesn't,
        # while the alternative setattr method works either way. 
      ds.save_as(outputFilePath)
      return True, None
    except Exception as err:
      return False, err
    
    

#
# DICOM_ModifyTest
#

class DICOM_ModifyTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_DICOM_Modify1()

  def test_DICOM_Modify1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('DICOM_Modify1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = DICOM_ModifyLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
