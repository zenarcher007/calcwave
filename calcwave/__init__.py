import sys
def audiostudio():
  try:
    from calcwave import calcwave as cw
    cw.main(sys.argv)
  except ModuleNotFoundError:
    # Run the dependency wizard
    from calcwave import dependencyWizard as dWizard
    dWizard.main(sys.argv)
    
    # Run calcwave again
    from calcwave import calcwave as cw
    cw.main(sys.argv)
