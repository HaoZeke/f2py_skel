! From https://rgoswami.me/posts/cython-derivedtype-f2py/
module vec
  use, intrinsic :: iso_c_binding
  implicit none

  type, bind(c) :: cartesian
     real(c_double) :: x,y,z
  end type cartesian

  contains

  subroutine unit_move(array) bind(c)
    type(cartesian), intent(inout) :: array
    print*, "Modifying the derived type now!"
    array%x=array%x+1
    array%y=array%y+1
    array%z=array%z+1
  end subroutine unit_move

end module vec
