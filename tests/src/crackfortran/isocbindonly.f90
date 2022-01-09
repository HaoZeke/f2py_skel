module vec
  ! use, intrinsic :: iso_c_binding
  use iso_c_binding, only: c_float, c_double
  implicit none

  type, bind(c) :: cartesian
     real(c_float) :: x(2),y,z
  end type cartesian

  type, bind(c) :: radial
     real(c_double) :: rad, theta
  end type radial

  ! type, bind(c) :: two_point
  !     type(cartesian) :: x(2)
  ! end type two_point

  contains

  subroutine unit_move(array, di) bind(c)
    type(cartesian), intent(inout) :: array!, r
    real(c_float), intent(in) :: di
    print*, "Modifying the derived type now!"
    array%x(1)=array%x(1)+di
    array%x(2)=array%x(2)+di
    array%y=array%y+di
    array%z=array%z+di
    print*, "Done modifying"
  end subroutine unit_move

end module vec
