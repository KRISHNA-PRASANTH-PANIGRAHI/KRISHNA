import '/flutter_flow/flutter_flow_util.dart';
import '/index.dart';
import 'cart_checkout_widget.dart' show CartCheckoutWidget;
import 'package:expandable/expandable.dart';
import 'package:flutter/material.dart';

class CartCheckoutModel extends FlutterFlowModel<CartCheckoutWidget> {
  ///  Local state fields for this page.

  bool? showCart = false;

  String zipCode = '';

  String? selectedAddress;

  bool showNewAddress = false;

  ///  State fields for stateful widgets in this page.

  final formKey = GlobalKey<FormState>();
  // State field(s) for Expandable widget.
  late ExpandableController expandableExpandableController;

  // State field(s) for address widget.
  FocusNode? addressFocusNode;
  TextEditingController? addressTextController;
  String? Function(BuildContext, String?)? addressTextControllerValidator;
  String? _addressTextControllerValidator(BuildContext context, String? val) {
    if (val == null || val.isEmpty) {
      return 'Please enter your address';
    }

    return null;
  }

  // State field(s) for streetAddress2 widget.
  FocusNode? streetAddress2FocusNode;
  TextEditingController? streetAddress2TextController;
  String? Function(BuildContext, String?)?
      streetAddress2TextControllerValidator;
  // State field(s) for city widget.
  FocusNode? cityFocusNode;
  TextEditingController? cityTextController;
  String? Function(BuildContext, String?)? cityTextControllerValidator;
  String? _cityTextControllerValidator(BuildContext context, String? val) {
    if (val == null || val.isEmpty) {
      return 'Please enter your city';
    }

    return null;
  }

  // State field(s) for state widget.
  FocusNode? stateFocusNode;
  TextEditingController? stateTextController;
  String? Function(BuildContext, String?)? stateTextControllerValidator;
  String? _stateTextControllerValidator(BuildContext context, String? val) {
    if (val == null || val.isEmpty) {
      return 'Choose a state';
    }

    return null;
  }

  // State field(s) for zip widget.
  FocusNode? zipFocusNode;
  TextEditingController? zipTextController;
  String? Function(BuildContext, String?)? zipTextControllerValidator;
  // State field(s) for zipCodeMobile widget.
  FocusNode? zipCodeMobileFocusNode;
  TextEditingController? zipCodeMobileTextController;
  String? Function(BuildContext, String?)? zipCodeMobileTextControllerValidator;

  @override
  void initState(BuildContext context) {
    addressTextControllerValidator = _addressTextControllerValidator;
    cityTextControllerValidator = _cityTextControllerValidator;
    stateTextControllerValidator = _stateTextControllerValidator;
  }

  @override
  void dispose() {
    expandableExpandableController.dispose();
    addressFocusNode?.dispose();
    addressTextController?.dispose();

    streetAddress2FocusNode?.dispose();
    streetAddress2TextController?.dispose();

    cityFocusNode?.dispose();
    cityTextController?.dispose();

    stateFocusNode?.dispose();
    stateTextController?.dispose();

    zipFocusNode?.dispose();
    zipTextController?.dispose();

    zipCodeMobileFocusNode?.dispose();
    zipCodeMobileTextController?.dispose();
  }
}
