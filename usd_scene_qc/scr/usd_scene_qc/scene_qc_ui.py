import os
from importlib import reload

import hou
from PySide2 import QtWidgets, QtCore, QtGui

from usd_scene_qc import _usd

reload(_usd)

"""
USDSceneQC is a QDialog widget for performing quality checks on a USD scene.

It scans the scene for:
- Missing references
- Broken attributes and primvars
- Missing render settings
- Invalid material bindings
"""


class USDSceneQC(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(USDSceneQC, self).__init__(parent=parent)
        self.selected_node = _usd.get_hou_selected_node()
        self.stage = self.selected_node.stage()

        self.resize(1050, 800)
        self.setWindowTitle('USD Scene QC')
        self.central_layout = QtWidgets.QVBoxLayout()
        self.central_layout.setAlignment(QtCore.Qt.AlignTop)

        # __________________________________________________
        # Add Parameters to check QGroupBox
        self.parms_to_check_grp = QtWidgets.QGroupBox()
        self.central_layout.addWidget(self.parms_to_check_grp)

        # Add Check References QCheckBox
        self.references_check = QtWidgets.QCheckBox("References")
        self.references_check.setChecked(True)
        self.central_layout.addWidget(self.references_check)

        # Add Check Material Binding QCheckBox
        self.mat_binding_check = QtWidgets.QCheckBox("Material Bindings")
        self.mat_binding_check.setChecked(True)
        self.central_layout.addWidget(self.mat_binding_check)

        # Add Check Missing Attributes and Primvars QCheckBox
        self.attribs_check = QtWidgets.QCheckBox("Attributes and Primvars")
        self.attribs_check.setChecked(True)
        self.central_layout.addWidget(self.attribs_check)

        # Add Check Render Settings QCheckBox
        self.render_settings_check = QtWidgets.QCheckBox("Render Settings")
        self.render_settings_check.setChecked(True)
        self.central_layout.addWidget(self.render_settings_check)

        # Add QC report QLabel
        self.qc_report_label = QtWidgets.QLabel("\nQC Report Output:\n")
        self.central_layout.addWidget(self.qc_report_label)

        # Add QC report list QListWidget
        self.qc_report_list = QtWidgets.QListWidget()
        self.central_layout.addWidget(self.qc_report_list)

        # Add Submit to Deadline QPushButton
        self.run_qc_button = QtWidgets.QPushButton("Run QC")
        self.central_layout.addWidget(self.run_qc_button)
        self.setLayout(self.central_layout)

        # Add Styles:
        script_dir = os.path.dirname(__file__)
        resources_path = os.path.join(script_dir, "..", "..", "resources")
        resources_path = os.path.normpath(resources_path)

        with open(os.path.join(resources_path, "style_hou.qss"), 'r') as f:
            self.setStyleSheet(f.read())

        # _____________________________
        # Buttons connections
        self.run_qc_button.clicked.connect(self.on_run_qc_button_clicked)

    def on_run_qc_button_clicked(self):
        """
         Populates the QC report list widget based on validation results.
        - If there are errors, they will be added to the QC report list.
        - If all QC checks are disabled, a warning message will be shown
        - If no errors are found, a 'QC Passed' message will be displayed.

        """
        self.qc_report_list.clear()
        errors = self.get_errors()
        if errors:
            for error in errors:
                if error:
                    item = QtWidgets.QListWidgetItem(error.message)
                    self.qc_report_list.addItem(item)

        elif self.is_all_unchecked():
            item = QtWidgets.QListWidgetItem("All QC checks are disabled — validation skipped.")
            self.qc_report_list.addItem(item)
        else:
            item = QtWidgets.QListWidgetItem("No errors detected — QC successful.")
            self.qc_report_list.addItem(item)

    def get_errors(self) -> list[_usd.ValidationError]:
        """
        Executes all currently enabled QC validators and returns a list of detected errors.

        Validators include:
        - Missing USD references
        - Primitives without material bindings
        - Invalid render settings, camera
        - Attribute validation
        :return: List of ValidationError

        """
        errors: list[_usd.ValidationError] = []
        if self.references_check.isChecked():
            errors += _usd.get_missing_references(self.stage)
        if self.mat_binding_check.isChecked():
            errors += _usd.validate_material_binding(self.stage)
        if self.render_settings_check.isChecked():
            errors += _usd.validate_render_primitives(self.stage)
        if self.attribs_check.isChecked():
            errors += _usd.validate_attributes(self.stage)

        return errors

    def is_all_unchecked(self) -> bool:
        """
        Checks if all validators are disabled.

        :return: True if all validators are turned off, False otherwise.
        """
        return not (self.references_check.isChecked() or
                    self.mat_binding_check.isChecked() or
                    self.render_settings_check.isChecked() or
                    self.attribs_check.isChecked())


dialog = None


def show_houdini():
    import hou
    global dialog
    dialog = USDSceneQC(parent=hou.qt.mainWindow())
    dialog.show()
    return dialog
