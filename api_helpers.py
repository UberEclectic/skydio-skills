def rotation_only(api):
    """ Helper to disable all vehicle motion, but still rotate to track a subject. """
    # Keep the subject centered in the frame
    api.focus.set_image_space(weight=1.0)

    # Don't move the vehicle in reaction to subject motion
    api.focus.set_range(weight=0)
    api.focus.set_elevation(weight=0)
    api.focus.set_keep_subject_in_sight(weight=0)
