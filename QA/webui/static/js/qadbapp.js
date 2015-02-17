var qadbApp = angular.module('qadbApp', []);

qadbApp.controller('EquipmentListCtrl', function ($scope, $http) {
  $http.get('/qadbapi/equipment').success(function(data) {
    $scope.equipment = data;
  });
  $scope.orderProp = 'name';
});

