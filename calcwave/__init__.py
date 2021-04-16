def audiostudio():
  try:
    from calcwave import calcwave as cw
    cw.main()
  except ModuleNotFoundError:
    # Run the dependency wizard
    from calcwave import dependencyWizard as dWizard
    dWizard.main()
    
    # Run calcwave again
    from calcwave import calcwave as cw
    cw.main()
