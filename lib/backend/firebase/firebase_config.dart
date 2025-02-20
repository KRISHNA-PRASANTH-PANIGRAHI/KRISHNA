import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

Future initFirebase() async {
  if (kIsWeb) {
    await Firebase.initializeApp(
        options: FirebaseOptions(
            apiKey: "AIzaSyD6qRECdm7Fg0KXXziLqATplrr1KbSi2fU",
            authDomain: "guid-ed-oyeuug.firebaseapp.com",
            projectId: "guid-ed-oyeuug",
            storageBucket: "guid-ed-oyeuug.firebasestorage.app",
            messagingSenderId: "588329753367",
            appId: "1:588329753367:web:2a3f4ee9aef48d3918b552"));
  } else {
    await Firebase.initializeApp();
  }
}
