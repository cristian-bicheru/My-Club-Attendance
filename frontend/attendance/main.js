var backendHostUrl = 'https://backend-dot-myclubattendance.appspot.com';
$(function(){
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
	$('#renderFrame').empty();
        $('#logged-out').show();

      }
    // [END gae_python_state_change]

    });

  }

  // [START configureFirebaseLoginWidget]
  // Firebase log-in widget
  function configureFirebaseLoginWidget() {
    var uiConfig = {
      'signInSuccessUrl': '/attendance',
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
    $.ajax(backendHostUrl + '/myattendance', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      headers: {
        'Authorization': 'Bearer ' + userIdToken
      }
    }).then(function(data){
      $('#renderFrame').empty();
      $('#renderFrame').append($(data));
    });
  }  
  // Sign out a user
  var signOutBtn =$('#sign-out');
  signOutBtn.click(function(event) {
    event.preventDefault();

    firebase.auth().signOut().then(function() {
      console.log("Sign out successful");
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


function receive() {
  $.ajax(backendHostUrl + '/accountdata', {
    headers: {
      'Authorization': 'Bearer ' + userIdToken
    }
  }).then(function(data){
    $('#points').empty();
    $('#locationb').empty();
    // Iterate over user data to display user's notes from database.
    data.forEach(function(note){
      $('#locationb').append($('<h4 style="letter-spacing:1px;margin:0;">').text(note.location));
      $('#points').append($('<h4 style="letter-spacing:1px;margin:0;">').text(note.points));
    });
  });
}
  configureFirebaseLogin();
  configureFirebaseLoginWidget();

});
