// Copyright 2016, Google, Inc.
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

$(function(){
  // This is the host for the backend.
  // TODO: When running Firenotes locally, set to http://localhost:8081. Before
  // deploying the application to a live production environment, change to
  // https://backend-dot-<PROJECT_ID>.appspot.com as specified in the
  // backend's app.yaml file.
  var backendHostUrl = 'https://backend-dot-myclubattendance.appspot.com';
  //var backendHostUrl = 'http://localhost:8081';

  // [START gae_python_firenotes_config]
  // Obtain the following from the "Add Firebase to your web app" dialogue
  // Initialize Firebase
  var config = {
    apiKey: "AIzaSyARD36F-FSRHnp4LNRiukES4yt0o6ohnGo",
    authDomain: "myclubattendance.firebaseapp.com",
    databaseURL: "https://myclubattendance.firebaseio.com",
    projectId: "myclubattendance",
    storageBucket: "myclubattendance.appspot.com",
    messagingSenderId: "311377687182"
  };
  // [END gae_python_firenotes_config]

  // This is passed into the backend to authenticate the user.
  var userIdToken = null;

  // Firebase log-in
  function configureFirebaseLogin() {

    firebase.initializeApp(config);

    // [START gae_python_state_change]
    firebase.auth().onAuthStateChanged(function(user) {
      if (user) {
        $('#logged-out').hide();
        var name = user.displayName;

        /* If the provider gives a display name, use the name for the
        personal welcome message. Otherwise, use the user's email. */
        var welcomeName = name ? name : user.email;

        user.getToken().then(function(idToken) {
          userIdToken = idToken;

          /* Now that the user is authenicated, fetch the notes. */
          register();
          renderHtml();

          $('#user').text(welcomeName);
          $('#logged-in').show();

        });

      } else {
        $('#logged-in').hide();
        $('#logged-out').show();

      }
    // [END gae_python_state_change]

    });

  }

  // [START configureFirebaseLoginWidget]
  // Firebase log-in widget
  function configureFirebaseLoginWidget() {
    var uiConfig = {
      'signInSuccessUrl': '/',
      'signInOptions': [
        // Leave the lines as is for the providers you want to offer your users.
        firebase.auth.GoogleAuthProvider.PROVIDER_ID
      ],
      // Terms of service url
      'tosUrl': '<your-tos-url>',
    };

    var ui = new firebaseui.auth.AuthUI(firebase.auth());
    ui.start('#firebaseui-auth-container', uiConfig);
  }
  // [END gae_python_firebase_login]

  // [START gae_python_fetch_notes]
  // Fetch notes from the backend.
  function register() {
    $.ajax(backendHostUrl + '/register', {
      headers: {
        'Authorization': 'Bearer ' + userIdToken
      },
      method: 'POST',
      contentType : 'application/json'
    });
  }
  // [END gae_python_fetch_notes]
  function renderHtml() {
    $.ajax(backendHostUrl + '/loadtallywindows', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      headers: {
        'Authorization': 'Bearer ' + userIdToken
      }
    }).then(function(data){
      if (data == '') {
         $('#tallyFrame').empty();
         $('#tallyFrame').append($('<h4>There are no active tally windows.</h4>'));
      } else {
         $('#tallyFrame').empty();
         $('#tallyFrame').append($(data));
      }
    });
  }
  // Sign out a user
  var signOutBtn =$('#sign-out');
  signOutBtn.click(function(event) {
    event.preventDefault();

    firebase.auth().signOut().then(function() {
      if (data == '') {
         $('#tallyFrame').empty();
         $('#tallyFrame').append($('<h4>There are no active tally windows.</h4>'));
      } else {
         $('#tallyFrame').empty();
         $('#tallyFrame').append($('<h4>Please sign in or register to see the active tally windows.</h4>'));
      }
    }, function(error) {
      console.log(error);
    });
  });

  // Save a note to the backend
  var saveNoteBtn = $('#add-note');
  saveNoteBtn.click(function(event) {
    event.preventDefault();

    var noteField = $('#location');
    var note = noteField.val();
    noteField.val("");

    /* Send note data to backend, storing in database with existing data
    associated with userIdToken */
    $.ajax(backendHostUrl + '/tally', {
      headers: {
        'Authorization': 'Bearer ' + userIdToken
      },
      method: 'POST',
      data: JSON.stringify({'club': note}),
      contentType : 'application/json'
    }).then(function(){
      // Refresh notebook display.
      fetchNotes();
    });

  });

  configureFirebaseLogin();
  configureFirebaseLoginWidget();

});
