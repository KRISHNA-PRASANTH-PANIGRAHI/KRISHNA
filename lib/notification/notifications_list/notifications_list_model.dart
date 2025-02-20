import '/flutter_flow/flutter_flow_util.dart';
import '/notification/user_information/user_information_widget.dart';
import 'notifications_list_widget.dart' show NotificationsListWidget;
import 'package:flutter/material.dart';

class NotificationsListModel extends FlutterFlowModel<NotificationsListWidget> {
  ///  State fields for stateful widgets in this page.

  // Models for userInformation dynamic component.
  late FlutterFlowDynamicModels<UserInformationModel> userInformationModels;

  @override
  void initState(BuildContext context) {
    userInformationModels =
        FlutterFlowDynamicModels(() => UserInformationModel());
  }

  @override
  void dispose() {
    userInformationModels.dispose();
  }
}
