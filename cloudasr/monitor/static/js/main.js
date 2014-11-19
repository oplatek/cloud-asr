var monitorApp = angular.module('monitorApp', []);

monitorApp.factory('socket', function ($rootScope) {
    var socket = io.connect();
    return {
        on: function (eventName, callback) {
            socket.on(eventName, function () {
                var args = arguments;
                $rootScope.$apply(function () {
                    callback.apply(socket, args);
                });
            });
        },
        emit: function (eventName, data, callback) {
            socket.emit(eventName, data, function () {
                var args = arguments;
                $rootScope.$apply(function () {
                    if (callback) {
                        callback.apply(socket, args);
                    }
                });
            })
        }
    };
});

monitorApp.config(function($interpolateProvider){
    $interpolateProvider.startSymbol('[[').endSymbol(']]');
});

monitorApp.controller('ContainersListCtrl', function($scope, $timeout, $http, socket) {
    $scope.containers ={};

    socket.on("connect", function() {
        socket.emit("stream_statuses", {})
        console.log("Socket connected");
    });

    socket.on("status_update", function(status) {
        if(status.address in $scope.containers) {
            $timeout.cancel($scope.containers[status.address]["timeout"])
        }

        $scope.containers[status.address] = status;
        $scope.containers[status.address]["timeout"] = $timeout(function() {
            $scope.containers[status.address]["status"] = "NOT RESPONDING";
        }, 10000);
    });

    $http.get('statuses').success(function(data) {
        var time = new Date().getTime() / 1000;

        angular.forEach(data.statuses, function(status) {
            $scope.containers[status.address] = status;

            if(time - status.time > 10) {
                $scope.containers[status.address]["status"] = "NOT RESPONDING";
            } else {
                $scope.containers[status.address]["timeout"] = $timeout(function() {
                    $scope.containers[status.address]["status"] = "NOT RESPONDING";
                }, 10000);
            }
        });
    });

});
