import '/cart_order_history/cart_product/cart_product_widget.dart';
import '/flutter_flow/flutter_flow_util.dart';
import 'cart_order_details_widget.dart' show CartOrderDetailsWidget;
import 'package:flutter/material.dart';

class CartOrderDetailsModel extends FlutterFlowModel<CartOrderDetailsWidget> {
  ///  State fields for stateful widgets in this page.

  // Model for cartProduct component.
  late CartProductModel cartProductModel;

  @override
  void initState(BuildContext context) {
    cartProductModel = createModel(context, () => CartProductModel());
  }

  @override
  void dispose() {
    cartProductModel.dispose();
  }
}
